import os

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TELEGRAM_SECRET = os.environ["TELEGRAM_SECRET"]

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MODEL_STT = os.environ.get("GROQ_MODEL_STT", "whisper-large-v3-turbo")

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]          # "owner/repo"
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

SCHEDULER_SECRET = os.environ["SCHEDULER_SECRET"]
TASKS_PATH = os.environ.get("TASKS_PATH", "tasks/tasks.md")
RECAPS_DIR = os.environ.get("RECAPS_DIR", "recaps")
TZ = os.environ.get("TZ", "Europe/Rome")
