from pyrogram import Client
import os
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

app = Client("uploader_session", api_id=API_ID, api_hash=API_HASH)

with app:
    print("\n✅ Session muvaffaqiyatli yaratildi!")
    print("Fayl nomi: uploader_session.session")
