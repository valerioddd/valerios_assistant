"""
Gira sul PC Windows dove e' installato Outlook (NON su Cloud Run).
Legge le mail non lette "task-like" e le inoltra al servizio Cloud Run.
Requisiti:  pip install pywin32 requests
Pianifica con Task Scheduler di Windows ogni 10-15 min.

AVVERTENZA: su PC gestito dalla banca l'esecuzione di script e/o il traffico
verso Cloud Run potrebbero essere bloccati o vietati dalla policy aziendale.
Se CLOUD_RUN_URL non e' raggiungibile, le mail finiscono in outlook_pending.txt
per inoltro manuale.
"""
import datetime
import json
import os
import pathlib
import requests
import win32com.client

CLOUD_RUN_URL = os.environ.get("CLOUD_RUN_URL", "")      # es. https://task-assistant-xxx.run.app
SCHEDULER_SECRET = os.environ.get("SCHEDULER_SECRET", "")
LOOKBACK_MIN = int(os.environ.get("LOOKBACK_MIN", "15"))
PENDING = pathlib.Path("outlook_pending.txt")
KEYWORDS = ("task", "attivit", "richiesta", "deadline", "scadenza", "entro", "assegn")


def recent_unread():
    ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox = ns.GetDefaultFolder(6)  # olFolderInbox
    items = inbox.Items
    items.Sort("[ReceivedTime]", True)
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=LOOKBACK_MIN)
    out = []
    for it in items:
        try:
            if it.Class != 43 or not it.UnRead:  # 43 = olMail
                continue
            if it.ReceivedTime.replace(tzinfo=None) < cutoff:
                break
            if not any(k in f"{it.Subject} {it.Body}".lower() for k in KEYWORDS):
                continue
            out.append({"from": str(it.SenderName), "subject": str(it.Subject), "body": str(it.Body)})
        except Exception:
            continue
    return out


def forward(mail):
    if not CLOUD_RUN_URL:
        return False
    try:
        r = requests.post(
            f"{CLOUD_RUN_URL}/outlook", json=mail,
            headers={"X-Scheduler-Secret": SCHEDULER_SECRET}, timeout=30,
        )
        return r.ok
    except requests.RequestException:
        return False


def main():
    for mail in recent_unread():
        if not forward(mail):
            with PENDING.open("a", encoding="utf-8") as f:
                f.write(json.dumps(mail, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
