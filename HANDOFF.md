# Prompt di handoff per nuova sessione (VS Code / Claude Code)

Incolla il blocco sotto come primo messaggio, con la cartella `assistant-gcp` aperta nel workspace.

---

Sei uno sviluppatore esperto. Riprendi un progetto già deciso e in gran parte implementato: un assistente personale per la gestione task. Io sono uno sviluppatore senior (Java/React/Angular, team lead), quindi niente spiegazioni base.

PREFERENZE DI RISPOSTA: conciso e diretto, niente preamboli/riepiloghi/disclaimer superflui, vai al punto. Elenchi solo se utili. Se ambiguo, UNA sola domanda di chiarimento. Codice: solo l'essenziale, commenti minimi, no spiegazione riga per riga salvo richiesta. Rispondi in italiano.

OBIETTIVO
Assistente che: (1) riceve note vocali Telegram per aggiornamenti/recap, (2) le trascrive ed elabora con un LLM, (3) salva/aggiorna task e recap come markdown su GitHub, (4) manda un riepilogo dei task alle 8:00 e 19:00 (Europe/Rome) su Telegram, con possibilità di riprioritizzare rispondendo in vocale, (5) opzionalmente rileva task da Outlook.

STACK DEFINITIVO (scelto e non da rimettere in discussione)
- Host: Google Cloud Run (FastAPI/Python), regione europe-west8 (Milano). Scale-to-zero.
- Scheduler: Cloud Scheduler, 2 job HTTP alle 8:00 e 19:00 con timezone NATIVO Europe/Rome (niente trucchi UTC).
- Trascrizione: Groq Whisper (whisper-large-v3-turbo), lingua "it". Gratis.
- LLM: Groq llama-3.3-70b-versatile, response_format json_object. Gratis. (Claude è un drop-in opzionale nel punto classify se un giorno aggiungo una key Anthropic; NON ora, per restare gratis.)
- Storage: markdown su GitHub via REST API. tasks/tasks.md (una riga per task: "- [ALTA|MEDIA|BASSA] descrizione — note/scadenza", ordinato per priorità) e recaps/YYYY-MM-DD.md (note della giornata).
- Telegram: bot via webhook, filtrato sul mio solo chat_id.

CODEBASE GIÀ ESISTENTE (nel workspace, non ricrearla da zero)
- app/main.py        FastAPI: /telegram (webhook, elabora in BackgroundTasks), /recap (scheduler), /outlook, /health. Header-secret su tutti.
- app/brain.py       Groq: transcribe() + classify_and_act() che ritorna JSON {action: update_tasks|add_note|both, new_tasks_md, recap_note, reply}.
- app/github_store.py read_file/write_file/append_to_file (httpx async, base64 UTF-8, gestione sha).
- app/telegram.py    send_message + download_voice.
- app/config.py      env vars.
- Dockerfile, requirements.txt (fastapi, uvicorn, httpx — niente anthropic).
- deploy.sh          one-shot: abilita API, deploy Cloud Run, crea i 2 job scheduler, setWebhook Telegram, init tasks.md, stampa URL + SCHEDULER_SECRET.
- outlook_reader.py  script LOCALE Windows (pywin32) che legge le mail non lette "task-like" e le POSTa su /outlook. Gira sul PC, non su Cloud Run.

VARIABILI D'AMBIENTE: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_SECRET, GROQ_API_KEY, GROQ_MODEL, GROQ_MODEL_STT, GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH, SCHEDULER_SECRET, TASKS_PATH, RECAPS_DIR, TZ.

DEPLOY (lo lancio io sulla mia macchina, serve gcloud CLI autenticato):
export PROJECT_ID=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... GROQ_API_KEY=... GITHUB_TOKEN=... GITHUB_REPO=owner/repo ; bash deploy.sh

VINCOLI E CAVEAT (importanti, non ignorarli)
- Le credenziali (bot Telegram, key Groq, token GitHub, progetto GCP) le creo io: tu non puoi generarle.
- Outlook è AZIENDALE (tenant banca). Microsoft Graph richiede consenso admin → non praticabile. L'unica via è lo script COM locale, ma su PC gestito dalla banca esecuzione script e uscita verso Cloud Run POTREBBERO essere bloccate dalla policy: in tal caso fallback a outlook_pending.txt / inoltro manuale. Teams è FUORI scope.
- Groq free tier: rate limit per-organizzazione (llama-3.3-70b ~1000 req/giorno, Whisper ~8h/giorno). Per il mio uso sono ordini di grandezza sotto.
- Cloud Run + Scheduler restano nel free tier ma richiedono fatturazione GCP attiva (carta, anche se non pago).

MIGLIORIE ESPLICITAMENTE RIMANDATE (non aggiungerle salvo mia richiesta): comando testuale /priorità, retry su 429 Groq, retry su conflitto sha GitHub.

STATO: codice completo e verificato a livello di sintassi + logica pura (base64 UTF-8, parsing JSON LLM). Manca solo il deploy reale e il test end-to-end. Partiamo da lì: aiutami a eseguire deploy.sh e a diagnosticare eventuali errori (tipicamente permessi IAM, abilitazione API, o policy GitHub token).
