from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
APP_PORT = int(os.getenv('APP_PORT', '8090'))
MCP_HOST = os.getenv('MCP_HOST', '0.0.0.0')
MCP_PORT = int(os.getenv('MCP_PORT', '8099'))
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', f'http://127.0.0.1:{APP_PORT}')
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Kolkata')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

DATA_ROOT = Path(os.getenv('DATA_ROOT', str(BASE_DIR / 'data')))
LOG_ROOT = Path(os.getenv('LOG_ROOT', str(BASE_DIR / 'logs')))
RUN_ROOT = Path(os.getenv('RUN_ROOT', str(BASE_DIR / 'run')))
SQLITE_PATH = Path(os.getenv('SQLITE_PATH', str(DATA_ROOT / 'db' / 'factory_analytics.db')))

FRIGATE_URL = os.getenv('FRIGATE_URL', '').rstrip('/')
FRIGATE_AUTH_MODE = os.getenv('FRIGATE_AUTH_MODE', 'none')
FRIGATE_USERNAME = os.getenv('FRIGATE_USERNAME', '')
FRIGATE_PASSWORD = os.getenv('FRIGATE_PASSWORD', '')
FRIGATE_BEARER_TOKEN = os.getenv('FRIGATE_BEARER_TOKEN', '')
FRIGATE_VERIFY_TLS = os.getenv('FRIGATE_VERIFY_TLS', 'false').lower() == 'true'

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
OLLAMA_VISION_MODEL = os.getenv('OLLAMA_VISION_MODEL', 'qwen2.5-vl:7b')
OLLAMA_TIMEOUT_SEC = int(os.getenv('OLLAMA_TIMEOUT_SEC', '120'))
OLLAMA_KEEP_ALIVE = os.getenv('OLLAMA_KEEP_ALIVE', '5m')

ANALYSIS_INTERVAL_SECONDS = int(os.getenv('ANALYSIS_INTERVAL_SECONDS', '300'))
SCHEDULER_ENABLED = os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true'
MCP_TOKEN = os.getenv('MCP_TOKEN', 'change-me')

for path in [DATA_ROOT, LOG_ROOT, RUN_ROOT, SQLITE_PATH.parent, DATA_ROOT / 'evidence' / 'snapshots', DATA_ROOT / 'reports' / 'daily']:
    path.mkdir(parents=True, exist_ok=True)
