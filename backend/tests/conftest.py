"""Pytest configuration."""

import asyncio
import os

os.environ.setdefault("USE_MOCK_LLM", "true")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://invoiceguard:invoiceguard@localhost:5432/invoiceguard")
