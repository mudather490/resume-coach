"""Windows-safe backend launcher.

Uvicorn on Windows defaults to the IOCP ProactorEventLoop, which dies with
"OSError [WinError 64] The specified network name is no longer available"
when the network stack changes (VPN/sleep/adapter resets) and takes the
whole server down — surfacing in the UI as "Backend unreachable".

This launcher forces the SelectorEventLoop, which does not use IOCP.

Usage:
    python run_backend.py            # serve on BACKEND_PORT (default 8000)
"""
import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload="--reload" in sys.argv,
    )
