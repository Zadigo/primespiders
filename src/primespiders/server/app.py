from collections.abc import Sequence

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException

from src.primespiders.observer import PerformanceModel
from src.primespiders.server.models import (
    ListSpidersModel,
    UrlsToVisitModel,
    WsReceiveMessage,
)
from src.primespiders.utils.clients import get_redis

app = FastAPI()

@app.websocket("/spider/{spider_id}")
async def get_spider(websocket: WebSocket, spider_id: str):
    """A websocket endpoint to get the status of a spider."""
    await websocket.accept()
    redisdb = get_redis()
    subscription = redisdb.pubsub()
    subscription.subscribe(f"{spider_id}")

    try:
        while True:
            spider_message = subscription.listen()
            data = WsReceiveMessage(**await websocket.receive_json())
            await websocket.send_json(spider_message)
    except WebSocketDisconnect:
        await websocket.close()
    except WebSocketException:
        await websocket.close()


@app.get("/spider/{spider_id}/urls-to-visit")
async def get_spider_urls_to_visit(spider_id: str) -> Sequence[UrlsToVisitModel]:
    """An endpoint to get the URLs that a spider needs to visit."""
    redisdb = get_redis()
    urls = redisdb.smembers(f"primespiders:{spider_id}:urls_to_visit")
    return [UrlsToVisitModel(url=url.decode()) for url in urls]


@app.get("/spider/{spider_id}/seen-urls")
async def get_spider_seen_urls(spider_id: str) -> Sequence[UrlsToVisitModel]:
    """An endpoint to get the URLs that a spider has already seen."""
    redisdb = get_redis()
    urls = redisdb.smembers(f"primespiders:{spider_id}:seen_urls")
    return [UrlsToVisitModel(url=url.decode()) for url in urls]


@app.get("/spiders")
async def list_all_spiders() -> Sequence[ListSpidersModel]:
    """An endpoint to list all spiders."""
    redisdb = get_redis()
    values = redisdb.keys("primespiders:*:seen_urls")

    spiders = []
    for value in values:
        referenceid = value.decode().split(":")[1]
        performance_key = f"primespiders:{referenceid}__performance"
        keys = redisdb.keys(performance_key)

        performance = PerformanceModel()

        if keys is not None:
            response = redisdb.hgetall(performance_key)
            performance.urls_to_visit_count = int(response.get(b'urls_to_visit_count', 0))
            performance.visited_urls_count = int(response.get(b'visited_urls_count', 0))
            performance.seen_urls_count = int(response.get(b'seen_urls_count', 0))
            performance.completion_pct = float(response.get(b'completion_pct', 0.0))
            performance.total_pct_urls_visited = float(response.get(b'total_pct_urls_visited', 0.0))
            performance.last_seen_url = response.get(b'last_seen_url', b'').decode()
            performance.last_updated = response.get(b'last_updated', b'').decode()

        spiders.append(ListSpidersModel(name=referenceid, performance=performance))

    return spiders
