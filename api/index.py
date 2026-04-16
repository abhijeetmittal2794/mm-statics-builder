"""Vercel serverless entry point.

Vercel's Python runtime detects this file and routes all requests through it.
The FastAPI app handles routing internally.
"""
import sys
from pathlib import Path

# Ensure project root is on the path so `from src.*` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.app.server import app
