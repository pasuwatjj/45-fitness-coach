"""Bundled translations of fixed application text only. No external translation calls."""
import json,re
from pathlib import Path
TEXT=json.loads((Path(__file__).parent/'static/translations.json').read_text(encoding='utf-8'))
PATTERN=re.compile('|'.join(re.escape(k) for k in sorted(TEXT,key=len,reverse=True)))
def english(text):
    if text.strip() in TEXT:return text.replace(text.strip(),TEXT[text.strip()])
    return PATTERN.sub(lambda m: m.group() if (re.match('[ก-๙]',m.group()) and m.start() and re.match('[ก-๙]',text[m.start()-1])) or (re.search('[ก-๙]$',m.group()) and m.end()<len(text) and re.match('[ก-๙]',text[m.end()])) else TEXT[m.group()],text)
