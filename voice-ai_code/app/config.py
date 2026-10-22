"""Shared settings for the voice server and all authenticated routes."""
import os
from pathlib import Path
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")
load_dotenv(APP_DIR.parents[1] / ".env")

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
ISSUER = "simple-auth-server"
