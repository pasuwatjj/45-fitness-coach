"""Fixed Thai coaching speech with cache; personal/camera data is never sent."""
import asyncio
import io
import json
import os
from pathlib import Path
import threading
import time
from urllib.request import Request, urlopen

PHRASES = {
    'enabled': 'เปิดเสียงแล้ว พร้อมช่วยดูฟอร์มนะ',
    'arm': 'ลองให้ศอกอยู่ใกล้ลำตัวอีกนิดนะ แล้วค่อย ๆ ยก',
    'torso': 'ลองกลับมายืนตัวตรง ผ่อนจังหวะและคุมลำตัวให้นิ่งนะ',
    'flexion': 'ลองงอศอกเพิ่มอีกนิดเท่าที่สบาย โดยไม่ยกต้นแขนตามนะ',
    'extension': 'ค่อย ๆ ลดแขนลงเพิ่มเท่าที่สบาย ไม่ต้องฝืนล็อกศอกนะ',
    'tempo': 'ลองผ่อนจังหวะลงนิดหนึ่ง คุมแรงตอนยกและตอนลดนะ',
    'rest': 'จบเซตแล้ว เก่งมาก พักก่อนนะ ดูคำแนะนำสำหรับเซตถัดไปได้เลย',
    'ready': 'พร้อมแล้ว เริ่มยกได้เลย ค่อย ๆ ทำตามจังหวะที่สบาย',
    'setup': 'ปล่อยแขนลง ต้นแขนอยู่ใกล้ลำตัว แล้วค้างนิ่งสองวินาทีนะ',
    'tracking': 'ลองจัดกล้องให้เห็นไหล่ ศอก และข้อมือครบอีกนิดนะ',
    'frame': 'ลองจัดกล้องตามคำแนะนำของท่านี้ ให้เห็นข้อต่อที่ต้องใช้ครบก่อนนะ',
    'position': 'ค่อย ๆ จัดท่าเริ่มต้นตามคำแนะนำบนจอ แล้วค้างนิ่งสองวินาทีนะ',
    'steady': 'ลองคุมลำตัวให้นิ่งขึ้นอีกนิด ถ้าต้องเหวี่ยงช่วย ลองลดน้ำหนักนะ',
    'upper_still': 'คุมต้นแขนให้นิ่ง แล้วขยับด้วยการงอและเหยียดศอกนะ',
    'soft_elbow': 'ผ่อนศอกเล็กน้อยและรักษามุมไว้ ไม่ต้องงอแขนเข้าหาตัวมากนะ',
    'raise_height': 'ยกประมาณระดับไหล่ก็พอ แล้วค่อย ๆ ลดกลับนะ',
    'knee_bend': 'ลองดันสะโพกไปหลังและผ่อนเข่าเล็กน้อย ไม่ย่อตัวเป็นสควอตนะ',
}
from exercises import EXERCISES
from localization import english
PHRASES.update({
 'range_option':'นับให้แล้วนะ ถ้าควบคุมได้และอยากเพิ่มช่วงยก ลองลดมุมเป้าหมายทีละ 5 องศา ไม่ต้องฝืนนะ',
 'grip_curl':'ลองหงายฝ่ามือไปด้านหน้า ศอกอยู่ข้างตัวนะ',
 'grip_hammer':'ลองจับแบบนิ้วโป้งชี้ขึ้น ฝ่ามือเข้าหากันนะ',
 'wrist':'ลองรักษาข้อมือให้ต่อแนวกับปลายแขน ไม่พับช่วยยกนะ',
 'shoulders':'ลองวางไหล่ให้สมดุล ไม่เอียงตัวช่วยยกนะ'})
for ex in EXERCISES:
    PHRASES['teach_'+ex['id']]=ex['teaching']
PHRASES.update({'en__'+key:english(value) for key,value in list(PHRASES.items())})
from strict_form import MESSAGES as STRICT_MESSAGES
for code,(thai,eng) in STRICT_MESSAGES.items():
    PHRASES['strict_'+code]=thai
    PHRASES['en__strict_'+code]=eng
PROVIDERS=('online','neural_female','neural_male','openai')


class VoiceCache:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.locks = {(provider,key): threading.Lock() for provider in PROVIDERS for key in PHRASES}
        self.failed_at = {}

    def configuration(self):
        return dict(openai_available=bool(os.environ.get('OPENAI_API_KEY')),
                    default='auto',minimum_speed=.7,maximum_speed=1.4)

    async def neural_audio(self, text, provider, language='th'):
        import edge_tts
        name='th-TH-PremwadeeNeural' if provider=='neural_female' else 'th-TH-NiwatNeural'
        if language=='en':name='en-US-JennyNeural' if provider=='neural_female' else 'en-US-GuyNeural'
        speech=edge_tts.Communicate(text,name,rate='-5%',volume='+0%',pitch='+0Hz',
                                   connect_timeout=4,receive_timeout=7)
        chunks=[]
        async for item in speech.stream():
            if item['type']=='audio':
                chunks.append(item['data'])
        return b''.join(chunks)

    def generate(self, code, provider):
        text=PHRASES[code]
        language='en' if code.startswith('en__') else 'th'
        if provider=='online':
            from gtts import gTTS
            buffer=io.BytesIO()
            gTTS(text,lang=language,lang_check=False,timeout=(4,6)).write_to_fp(buffer)
            return buffer.getvalue()
        if provider.startswith('neural_'):
            return asyncio.run(asyncio.wait_for(self.neural_audio(text,provider) if language=='th' else self.neural_audio(text,provider,'en'),timeout=15))
        key=os.environ.get('OPENAI_API_KEY')
        if not key:
            raise RuntimeError('OpenAI API key is not configured')
        payload=dict(model='gpt-4o-mini-tts',voice='coral',input=text,response_format='mp3',
            instructions=('Speak English clearly' if language=='en' else 'Speak Thai clearly')+' in a warm, calm, kind and encouraging fitness coach voice. '
                         'Use natural conversational phrasing, a gentle tone and a relaxed pace. '
                         'Do not exaggerate emotion or add words.')
        req=Request('https://api.openai.com/v1/audio/speech',data=json.dumps(payload).encode('utf-8'),
                    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
        with urlopen(req,timeout=20) as response:
            return response.read(2_000_000)

    def audio(self, code, provider='online'):
        if code not in PHRASES or provider not in PROVIDERS:
            raise ValueError('Unknown voice phrase or provider')
        if provider=='openai' and not self.configuration()['openai_available']:
            raise RuntimeError('OpenAI API key is not configured')
        cache_key=(provider,code)
        with self.locks[cache_key]:
            path=self.folder/provider/(code+'.mp3')
            if path.is_file() and path.stat().st_size>100:
                return path.read_bytes()
            if time.monotonic()-self.failed_at.get(cache_key,-1000)<30:
                raise RuntimeError('Online voice is temporarily unavailable')
            try:
                data=self.generate(code,provider)
                if len(data)<=100:
                    raise RuntimeError('Empty voice response')
                path.parent.mkdir(parents=True,exist_ok=True)
                temporary=path.with_suffix('.tmp')
                temporary.write_bytes(data)
                temporary.replace(path)
                return data
            except Exception:
                self.failed_at[cache_key]=time.monotonic()
                raise
