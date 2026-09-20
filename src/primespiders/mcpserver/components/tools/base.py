from fastmcp.tools import tool


@tool
def list_spiders():
    pass


@tool
def get_spider(spider_id: str):
    pass


@tool
def list_spider_seen_urls(spider_id: str):
    pass


@tool
def list_spider_urls_to_visit(spider_id: str):
    pass
