#!/usr/bin/env python3
"""Compatibility entry point for the FastAPI server."""

import os

import uvicorn

from cinesense.api.server import app  # noqa: F401


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("cinesense.api.server:app", host=host, port=port, reload=False)
