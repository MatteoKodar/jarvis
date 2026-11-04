import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

def mode():
    value = os.getenv("JARVIS_MODE", "DEMO").upper()
    if value not in {"DEMO", "LIVE"}:
        raise ValueError("JARVIS_MODE måste vara DEMO eller LIVE")
    return value

def data_dir():
    path = Path(os.getenv("JARVIS_DATA_DIR", str(ROOT / "data"))).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path

def db_path():
    return data_dir() / (mode().lower() + ".sqlite3")

def missing_live():
    from decimal import Decimal, InvalidOperation
    missing = []
    for key in ["OPENAI_API_KEY", "JARVIS_MODEL", "JARVIS_PRICE_VERSION", "JARVIS_PRICED_MODEL"]:
        if not os.getenv(key):
            missing.append(key)
    for key in ["JARVIS_INPUT_USD", "JARVIS_OUTPUT_USD", "JARVIS_USD_SEK"]:
        try:
            value = Decimal(os.getenv(key, ""))
            if not value.is_finite() or value <= 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            missing.append(key)
    if os.getenv("JARVIS_PAID_ENABLED") != "true":
        missing.append("JARVIS_PAID_ENABLED=true")
    if os.getenv("JARVIS_RESEARCH_ENABLED") != "true":
        missing.append("JARVIS_RESEARCH_ENABLED=true")
    return missing

