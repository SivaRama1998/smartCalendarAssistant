# background_process.py

from telegram_otp_auth import start_auth_flow
import os
from dotenv import load_dotenv
from telethon import TelegramClient

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH_KEY")
SESSION_FILE=os.getenv("SESSION_FILE")

print("Starting Telegram auth flow...")

if os.path.exists(SESSION_FILE):
    print("Session file already exists. Loading session...")
    with open(SESSION_FILE, "r") as f:
        session_string = f.read()
else:
    print("Session file not found. Starting new auth flow...")
    # Start the auth flow
    start_auth_flow()

print("Authentication complete. Now you can continue with the saved session.")

#end of file