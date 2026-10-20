"""Default startup policy; no settings page can start the upstream worker bundle.

This is a startup boundary, not a sandbox for all upstream HTTP/tool handlers.
The remaining handlers are tracked in docs/shenxiao/FOUNDATION.md.
"""

from contextlib import asynccontextmanager
import os


def upstream_runtime_enabled() -> bool:
    return os.environ.get("SHENXIAO_ENABLE_UPSTREAM_RUNTIME") == "1"


@asynccontextmanager
async def chat_only_lifespan(*, initialize, restore, close):
    try:
        await initialize()
        await restore()
        yield
    finally:
        await close()
