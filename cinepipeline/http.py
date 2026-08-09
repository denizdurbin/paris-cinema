import asyncio
from contextlib import asynccontextmanager

import httpx

USER_AGENT = "paris-cinema-app/1.0 (personal project)"
TIMEOUT = 20.0
MAX_CONCURRENCY = 4
MIN_DELAY = 0.3

GATE = asyncio.Semaphore(MAX_CONCURRENCY)


@asynccontextmanager
async def client():
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"},
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as c:
        yield c


async def get_text(c: httpx.AsyncClient, url: str) -> str:
    async with GATE:
        resp = await c.get(url)
        await asyncio.sleep(MIN_DELAY)
    resp.raise_for_status()
    return resp.text


async def get_json(c: httpx.AsyncClient, url: str):
    async with GATE:
        resp = await c.get(url)
        await asyncio.sleep(MIN_DELAY)
    resp.raise_for_status()
    return resp.json()
