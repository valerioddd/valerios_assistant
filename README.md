# Assistente task — GCP (Cloud Run + Cloud Scheduler) + Groq + GitHub + Telegram

Nota vocale su Telegram → trascrizione **Groq Whisper** (IT) → **Llama 3.3 70B** (Groq) decide se
aggiornare `tasks.md` o appendere al recap del giorno → commit su GitHub.
**Cloud Scheduler** invia il riepilogo alle **8:00** e **19:00** (timezone nativo Europe/Rome);
rispondi in vocale per riprioritizzare.

Costo: Groq/GitHub/Telegram gratis; Cloud Run e Cloud Scheduler restano nel free tier
(serve però un account di fatturazione GCP con carta, anche se non pagherai nulla).

## Credenziali da procurarti una volta
1. **Bot Telegram** (@BotFather → token) e il tuo **chat_id**
   (`https://api.telegram.org/bot<TOKEN>/getUpdates` → `message.chat.id`).
2. **Groq API key** — console.groq.com (no carta).
3. **GitHub**: un repo + token fine-grained con *Contents: Read and write* su quel repo.
4. **Progetto GCP** con fatturazione attiva, e **gcloud CLI** installato + `gcloud auth login`.

## Deploy in un comando
```bash
export PROJECT_ID=tuo-progetto
export TELEGRAM_BOT_TOKEN=...  TELEGRAM_CHAT_ID=...
export GROQ_API_KEY=...        GITHUB_TOKEN=...  GITHUB_REPO=owner/repo
bash deploy.sh
```
`deploy.sh` abilita le API, fa il deploy su Cloud Run (regione `europe-west8`, Milano),
crea i due job scheduler alle 8:00 e 19:00 Europe/Rome, registra il webhook Telegram,
inizializza `tasks/tasks.md` e stampa URL + `SCHEDULER_SECRET`.

Prova: manda una nota vocale al bot.

## File nel repo
- `tasks/tasks.md` — `- [ALTA] descrizione — note/scadenza` (ALTA/MEDIA/BASSA).
- `recaps/YYYY-MM-DD.md` — note della giornata, automatico.

## Outlook (opzionale, dipende dalla policy del PC aziendale)
Sul PC Windows con Outlook:
```
pip install pywin32 requests
set CLOUD_RUN_URL=https://task-assistant-xxx.run.app
set SCHEDULER_SECRET=<stampato da deploy.sh>
python outlook_reader.py
```
Pianifica con Task Scheduler ogni 10-15 min. Se l'uscita verso Cloud Run e' bloccata,
le mail finiscono in `outlook_pending.txt` (inoltro manuale). L'accesso via Microsoft Graph
al tenant aziendale non e' praticabile senza consenso admin: questa e' la sola via locale.

## Note
- Cloud Run scala a zero: la prima nota vocale dopo inattivita' paga un cold start di pochi secondi (Telegram ritenta, nessun messaggio perso).
- Scheduler con timezone nativo: niente trucchi UTC, i recap sono alle 8 e 19 di Roma anche col cambio ora legale.
- Gli endpoint sono `--allow-unauthenticated` ma protetti dai secret negli header.
- Claude e' sostituibile a Groq nel punto `brain.classify_and_act` se un giorno aggiungi una key Anthropic (non gratis).
