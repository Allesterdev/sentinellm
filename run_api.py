#!/usr/bin/env python3
"""
SentineLLM API Server
Run with: python run_api.py
"""

import uvicorn

from src.api.app import create_app
from src.api.config import settings

if __name__ == "__main__":
    app = create_app()

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
        access_log=True,
    )
