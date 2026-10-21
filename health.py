"""Basic adult BMI screening and arithmetic from user-supplied measurements.

CDC general adult thresholds; BMI does not separate fat from muscle. Values
are not a diagnosis. Optional composition values must come from a measurement.
"""
from datetime import datetime, timedelta, date, timezone
import math

BMI_SOURCE='https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html'
BMI_LIMITS_SOURCE='https://www.cdc.gov/bmi/faq/index.html'


def number(data,key,label,low,high,optional=False):
    value=data.get(key)
    if optional and (value is None or value==''):
        return None
    if isinstance(value,bool) or value is None or not isinstance(value,(int,float,str)):
        raise ValueError(f'กรุณากรอก{label}เป็นตัวเลข')
    try:
        result=float(value)
    except (ValueError,TypeError):
        raise ValueError(f'กรุณากรอก{label}เป็นตัวเลข') from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f'{label}ต้องอยู่ระหว่าง {low:g}–{high:g}')
    return result


def normalize(data):
    if not isinstance(data,dict):
        raise ValueError('รูปแบบข้อมูลสุขภาพไม่ถูกต้อง')
    age=number(data,'age','อายุ (ปี)',2,120)
    if not age.is_integer():
        raise ValueError('อายุต้องเป็นจำนวนปีเต็ม')
    height=number(data,'height_cm','ส่วนสูง (ซม.)',50,250)
    weight=number(data,'weight_kg','น้ำหนัก (กก.)',5,350)
    fat=number(data,'body_fat_pct','เปอร์เซ็นต์ไขมันที่วัดได้',1,75,optional=True)
    muscle=number(data,'muscle_kg','มวลกล้ามเนื้อที่วัดได้ (กก.)',.1,350,optional=True)
    if muscle is not None and muscle > weight:
        raise ValueError('มวลกล้ามเนื้อที่กรอกต้องไม่เกินน้ำหนักตัว')
    if fat is not None and muscle is not None and muscle > weight*(1-fat/100)+.1:
        raise ValueError('ค่ากล้ามเนื้อสูงกว่ามวลที่ไม่ใช่ไขมัน ตรวจหน่วย กก. และเปอร์เซ็นต์ไขมันอีกครั้ง')
    goal=data.get('goal','fitness')
    if goal not in ('fitness','build','fatloss'):
        raise ValueError('เป้าหมายไม่ถูกต้อง')
    measured_on=data.get('measured_on')
    today=datetime.now(timezone(timedelta(hours=7))).date()
    if measured_on in (None,''):
        measured_on=today.isoformat()
    if not isinstance(measured_on,str):
        raise ValueError('วันที่วัดไม่ถูกต้อง')
    try:
        measured_date=date.fromisoformat(measured_on)
    except ValueError:
        raise ValueError('วันที่วัดไม่ถูกต้อง') from None
    if measured_date > today or measured_date.year < 1900:
        raise ValueError('วันที่วัดต้องไม่อยู่ในอนาคต')
    return dict(age=int(age),height_cm=height,weight_kg=weight,body_fat_pct=fat,
                muscle_kg=muscle,goal=goal,measured_on=measured_date.isoformat())


def analyze(data):
    inputs=normalize(data)
    bmi=inputs['weight_kg']/(inputs['height_cm']/100)**2
    if inputs['age'] < 20:
        category='อายุต่ำกว่า 20 ปี — ไม่ใช้เกณฑ์ผู้ใหญ่'
        category_key='not_adult'
        note='วัยเด็กและวัยรุ่นต้องประเมินตามอายุและเพศ เว็บนี้ยังไม่คำนวณ BMI percentile'
    else:
        if bmi < 18.5:category,category_key='ต่ำกว่าช่วงอ้างอิง BMI ทั่วไป','underweight'
        elif bmi < 25:category,category_key='อยู่ในช่วงอ้างอิง BMI ทั่วไป','reference'
        elif bmi < 30:category,category_key='สูงกว่าช่วงอ้างอิง BMI ทั่วไป','overweight'
        else:category,category_key='อยู่ในช่วง BMI ที่เรียกว่าภาวะอ้วนตามเกณฑ์ทั่วไป','obesity'
        note='BMI ใช้คัดกรองเบื้องต้นตามเกณฑ์ทั่วไป CDC อายุ 20 ปีขึ้นไป ไม่ใช่การวินิจฉัยหรือเกณฑ์เฉพาะคนไทย'
    fat=inputs['body_fat_pct']
    fat_mass=inputs['weight_kg']*fat/100 if fat is not None else None
    lean_mass=inputs['weight_kg']-fat_mass if fat_mass is not None else None
    tips=[
        'BMI แยกไขมันออกจากกล้ามเนื้อไม่ได้ คนที่มีกล้ามเนื้อเยอะอาจมี BMI สูงได้',
        'ดูแนวโน้มจากการวัดหลายครั้งด้วยวิธีเดิมและช่วงเวลาใกล้กัน เพื่อเทียบกันได้ง่ายขึ้น',
    ]
    if fat is None:
        tips.append('ยังไม่มีเปอร์เซ็นต์ไขมันจากเครื่องวัด จึงยังไม่คำนวณมวลไขมันหรือมวลที่ไม่ใช่ไขมัน')
    else:
        tips.append('มวลที่ไม่ใช่ไขมันรวมกล้ามเนื้อ กระดูก น้ำ และส่วนอื่น ๆ ไม่ใช่มวลกล้ามเนื้อเพียงอย่างเดียว')
    if inputs['muscle_kg'] is None:
        tips.append('มวลกล้ามเนื้อต้องนำค่าจากการวัดมากรอก เว็บไม่ได้คำนวณจาก BMI หรือภาพกล้อง')
    tips.append({'build':'เป้าหมายเพิ่มกล้าม: ติดตามน้ำหนักร่วมกับค่ากล้ามเนื้อที่วัดได้ ไม่ดู BMI เพียงค่าเดียว',
                 'fatloss':'เป้าหมายติดตามไขมัน: เทียบค่าไขมันที่วัดได้หลายครั้ง แทนการใช้ BMI สรุปไขมันอย่างเดียว',
                 'fitness':'เป้าหมายสุขภาพและความแข็งแรง: ใช้บันทึกนี้ติดตามแนวโน้ม ควบคู่กับความสามารถในการออกกำลังกาย'}[inputs['goal']])
    return dict(inputs=inputs,bmi=round(bmi,2),category=category,category_key=category_key,
                adult=inputs['age']>=20,standard='CDC general adult BMI',note=note,
                fat_mass_kg=round(fat_mass,2) if fat_mass is not None else None,
                lean_mass_kg=round(lean_mass,2) if lean_mass is not None else None,
                muscle_kg=inputs['muscle_kg'],tips=tips,sources=[BMI_SOURCE,BMI_LIMITS_SOURCE])
