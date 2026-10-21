"""Bundled translations of fixed application text only. No external translation calls."""
import json,re
from pathlib import Path
TEXT=json.loads((Path(__file__).parent/'static/translations.json').read_text(encoding='utf-8'))
PATTERN=re.compile('|'.join(re.escape(k) for k in sorted(TEXT,key=len,reverse=True)))
def english(text):
    if text.strip() in TEXT:return text.replace(text.strip(),TEXT[text.strip()])
    return PATTERN.sub(lambda m:TEXT[m.group()],text)
