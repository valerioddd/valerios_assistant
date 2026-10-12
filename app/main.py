import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, Header, HTTPException
from . import config, telegram, brain, github_store

app = FastAPI()


def _now():
    return datetime.now(ZoneInfo(config.TZ))


def _recap_path() -> str:
    return f"{config.RECAPS_DIR}/{_now():%Y-%m-%d}.md"


async def _process_text(text: str) -> str:
    current, _ = await github_store.read_file(config.TASKS_PATH)
    result = await brain.classify_and_act(current, text)
    action = result.get("action")
    if action in ("update_tasks", "both") and result.get("new_tasks_md"):
        await github_store.write_file(
            config.TASKS_PATH, result["new_tasks_md"].strip() + "\n",
            "chore(tasks): update via assistant",
        )
    if action in ("add_note", "both") and result.get("recap_note"):
        await github_store.append_to_file(
            _recap_path(), f"- {_now():%H:%M} — {result['recap_note'].strip()}",
            "docs(recap): add note via assistant",
        )
    return result.get("reply") or "Fatto."


async def _handle_telegram(msg: dict):
    try:
        if "voice" in msg:
            text = await brain.transcribe(await telegram.download_voice(msg["voice"]["file_id"]))
        elif "text" in msg:
            text = msg["text"]
        else:
            return
        reply = await _process_text(text)
        await telegram.send_message(f"📝 _{text}_\n\n{reply}")
    except Exception as e:
        traceback.print_exc()
        await telegram.send_message(f"⚠️ Errore: {e}")


@app.post("/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    if x_telegram_bot_api_secret_token != config.TELEGRAM_SECRET:
        raise HTTPException(403)
    update = await request.json()
    msg = update.get("message") or update.get("edited_message")
    if msg and str(msg["chat"]["id"]) == str(config.TELEGRAM_CHAT_ID):
        # inline: su Cloud Run la CPU è throttled dopo la response, i BackgroundTasks stallano
        await _handle_telegram(msg)
    return {"ok": True}


@app.post("/recap")
async def recap(x_scheduler_secret: str = Header(default="")):
    if x_scheduler_secret != config.SCHEDULER_SECRET:
        raise HTTPException(403)
    tasks, _ = await github_store.read_file(config.TASKS_PATH)
    body = tasks.strip() or "_Nessun task._"
    await telegram.send_message(
        f"⏰ *Riepilogo task ({_now():%H:%M})*\n\n{body}\n\n"
        "Rispondi con una nota vocale per riprioritizzare o aggiungere task."
    )
    return {"ok": True}


@app.post("/outlook")
async def outlook_ingest(request: Request, x_scheduler_secret: str = Header(default="")):
    if x_scheduler_secret != config.SCHEDULER_SECRET:
        raise HTTPException(403)
    p = await request.json()
    text = f"Email da {p.get('from','?')}. Oggetto: {p.get('subject','')}. Contenuto: {p.get('body','')[:1500]}"
    reply = await _process_text(text)
    await telegram.send_message(f"📧 *Nuova mail → task*\n{p.get('subject','')}\n\n{reply}")
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True}
