import httpx
from . import config

_BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


async def send_message(text: str, chat_id: str | None = None) -> None:
    body = {"chat_id": chat_id or config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{_BASE}/sendMessage", json=body)
        if r.status_code == 400:  # Markdown non parsabile (es. "_" nel testo)
            body.pop("parse_mode")
            r = await c.post(f"{_BASE}/sendMessage", json=body)
        if r.is_error:
            print(f"telegram sendMessage {r.status_code}: {r.text}")


async def download_voice(file_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(f"{_BASE}/getFile", params={"file_id": file_id})
        r.raise_for_status()
        path = r.json()["result"]["file_path"]
        f = await c.get(f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}/{path}")
        f.raise_for_status()
        return f.content
