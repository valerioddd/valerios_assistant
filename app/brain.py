import json
import httpx
from . import config

_GROQ = "https://api.groq.com/openai/v1"


async def transcribe(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    files = {"file": (filename, audio_bytes, "application/octet-stream")}
    data = {"model": config.GROQ_MODEL_STT, "language": "it", "response_format": "text"}
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{_GROQ}/audio/transcriptions", headers=headers, data=data, files=files)
    r.raise_for_status()
    return r.text.strip()


_SYS = """Sei l'agente di un assistente task personale (italiano).
Ricevi: (1) il contenuto attuale di tasks.md, (2) un testo (nota vocale o email).
Decidi l'azione e rispondi SOLO con JSON valido.

Formato tasks.md: lista markdown, una riga per task:
- [ALTA|MEDIA|BASSA] descrizione — note/scadenza
Ordina per priorità (ALTA in alto).

Schema risposta:
{"action":"update_tasks|add_note|both","new_tasks_md":"<intero tasks.md aggiornato o null>","recap_note":"<riga da appendere al recap o null>","reply":"<breve conferma in italiano>"}

Regole:
- aggiunge/completa/riprioritizza task -> update_tasks (rigenera l'intero file)
- aggiornamento della giornata senza modifiche ai task -> add_note
- entrambe -> both
- mantieni i task esistenti non citati; non inventare scadenze."""


async def classify_and_act(current_tasks: str, text: str) -> dict:
    payload = {
        "model": config.GROQ_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYS},
            {
                "role": "user",
                "content": f"<tasks_md>\n{current_tasks or '(vuoto)'}\n</tasks_md>\n\n<input>\n{text}\n</input>",
            },
        ],
    }
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{_GROQ}/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"].strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
