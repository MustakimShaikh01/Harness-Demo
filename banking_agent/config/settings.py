from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("BANKGUARD_DATA_DIR", str(BASE_DIR / "data")))
MODEL = os.getenv("BANKGUARD_MODEL", "gemini-flash-lite-latest")
ENVIRONMENT = os.getenv("BANKGUARD_ENV", "development")
LOG_LEVEL = os.getenv("BANKGUARD_LOG_LEVEL", "INFO")
ACTIVE_CUSTOMER_ID = os.getenv("BANKGUARD_DEMO_CUSTOMER", "cust_demo_001")
MAX_OUTPUT_TOKENS = int(os.getenv("BANKGUARD_MAX_OUTPUT_TOKENS", "384"))
if not 64 <= MAX_OUTPUT_TOKENS <= 2048:
    raise ValueError("BANKGUARD_MAX_OUTPUT_TOKENS must be between 64 and 2048")
