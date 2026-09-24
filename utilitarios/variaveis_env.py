import os 
import oracledb
from dotenv import load_dotenv

load_dotenv()


def safe_env_get(key):
    value = os.getenv(key)
    return value.strip() if value else None

def safe_env_get_split(value):
    if not value:
        return []
    return list(set([v.strip() for v in value.split(",") if v and v.strip()]))