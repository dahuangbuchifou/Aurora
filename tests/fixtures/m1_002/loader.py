from __future__ import annotations
import json
from pathlib import Path
from aurora.core.schema_registry import parse_object

ROOT=Path(__file__).resolve().parents[3]
EXAMPLES=ROOT/'schemas'/'examples'/'m1_002'
SCHEMAS=ROOT/'schemas'/'v1'
OBJECT_FILES=[
    EXAMPLES/'case_a_web'/'objects.json',
    EXAMPLES/'case_b_video'/'objects.json',
    EXAMPLES/'case_c_pdf'/'objects.json',
    EXAMPLES/'cross_case'/'topic_summary.json',
    EXAMPLES/'cross_case'/'insight.json',
    EXAMPLES/'cross_case'/'personal_opinion.json',
]
def _extract(payload):
    if isinstance(payload,dict) and 'objects' in payload: return payload['objects']
    if isinstance(payload,dict) and 'object_type' in payload: return [payload]
    return []
def load_raw_objects():
    raw=[]
    for path in OBJECT_FILES:
        raw.extend(_extract(json.loads(path.read_text(encoding='utf-8'))))
    return raw
def load_objects(): return [parse_object(item) for item in load_raw_objects()]
def object_map(): return {obj.id:obj for obj in load_objects()}
