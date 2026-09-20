from fastmcp import FastMCP
from fastmcp.server.providers.filesystem import FileSystemProvider

from src.primespiders.mcpserver.utils import BASE_DIR

app = FastMCP(
    name="Prime Spiders",
    version="0.1.0",
    providers=[
        FileSystemProvider(directory=BASE_DIR / "components")
    ]
)
