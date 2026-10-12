import base64
import httpx
from . import config

API = "https://api.github.com"
_H = {
    "Authorization": f"Bearer {config.GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "tg-task-assistant",
}


async def read_file(path: str) -> tuple[str, str | None]:
    url = f"{API}/repos/{config.GITHUB_REPO}/contents/{path}"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, headers=_H, params={"ref": config.GITHUB_BRANCH})
    if r.status_code == 404:
        return "", None
    r.raise_for_status()
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


async def write_file(path: str, content: str, message: str) -> None:
    _, sha = await read_file(path)
    url = f"{API}/repos/{config.GITHUB_REPO}/contents/{path}"
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": config.GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.put(url, headers=_H, json=body)
    r.raise_for_status()


async def append_to_file(path: str, text: str, message: str) -> None:
    existing, _ = await read_file(path)
    new = (existing.rstrip() + "\n\n" + text.strip() + "\n") if existing else text.strip() + "\n"
    await write_file(path, new, message)
