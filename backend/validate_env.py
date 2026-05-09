# validate_env.py
import os, json
from dotenv import load_dotenv
load_dotenv()

json_fields = ['ALLOWED_VIDEO_EXTENSIONS']  # agrega otros
for field in json_fields:
    val = os.getenv(field)
    try:
        json.loads(val or '[]')
        print(f'{field}: OK')
    except:
        print(f'{field}: FIX -> {val}')