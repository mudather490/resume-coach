"""Vercel FastAPI entrypoint for the `backend` service.

Vercel builds a service from its root directory. When the service root is
``backend/``, the deployed bundle starts at the contents of that folder
(``main.py``, ``db/``, ``chat/``, ...) instead of the repository root, so
``import backend.xxx`` would not resolve there.

This shim exposes the bundle root as the ``backend`` package when the repo-root
layout is not present, then exports the real ASGI app. Local development
(`uvicorn backend.main:app` from the repo root) is unaffected.
"""
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)

if os.path.isdir(os.path.join(_PARENT, "backend")):
    # Repo-root layout: normal `backend` package import.
    if _PARENT not in sys.path:
        sys.path.insert(0, _PARENT)
else:
    # Service-root bundle: this folder is the `backend` package.
    package = types.ModuleType("backend")
    package.__path__ = [_HERE]
    sys.modules.setdefault("backend", package)

from backend.main import app  # noqa: E402

__all__ = ["app"]
