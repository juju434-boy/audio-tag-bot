import os
import logging
import json
import requests
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your actual Telegram Bot Token
BOT_TOKEN = os.getenv("8865367032:AAEgu4lx7hhB2IdiYMaHod7P2DTYGuKIrkM", "8865367032:AAEgu4lx7hhB2IdiYMaHod7P2DTYGuKIrkM")
bot = Bot(token=BOT_TOKEN)

# Store user states to know what tag they want to edit
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎧 Welcome to the Audio Tag Editor Bot! \n"
        "Please send me an audio file (.mp3) you want to edit."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.document or not message.document.file_name.endswith('.mp3'):
        await message.reply_text("Please send an actual .mp3 file.")
        return

    # Download file to local storage
    file_id = message.document.file_id
    new_file = await context.bot.get_file(file_id)
    
    # Create an downloads directory if it doesn't exist
    os.makedirs('/tmp', exist_ok=True)
    file_path = f"/tmp/{message.document.file_name}"
    await new_file.download_to_drive(file_path)

    # Save state
    user_id = update.effective_user.id
    user_states[user_id] = {"file_path": file_path, "filename": message.document.file_name}

    # Read current tags
    try:
        audio = ID3(file_path)
        title = audio.get("TIT2", "Unknown")[0] if "TIT2" in audio else "Unknown"
        artist = audio.get("TPE1", "Unknown")[0] if "TPE1" in audio else "Unknown"
        album = audio.get("TALB", "Unknown")[0] if "TALB" in audio else "Unknown"
        
        await message.reply_text(
            f"🎵 **File Loaded:** {message.document.file_name}\n"
            f"🏷️ Current Tags:\n"
            f"Title: {title}\n"
            f"Artist: {artist}\n"
            f"Album: {album}\n\n"
            f"Reply with the new information in this exact format:\n"
            f"`Title: New Title\nArtist: New Artist\nAlbum: New Album`"
        )
    except Exception as e:
        audio = mutagen.File(file_path)
        await message.reply_text(
            "I loaded your file, but it doesn't have standard ID3 tags. "
            "Reply with tags in the format:\n`Title: ...\nArtist: ...\nAlbum: ...`"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text("Please send an audio file first!")
        return

    text = update.message.text
    file_path = user_states[user_id]["file_path"]
    original_name = user_states[user_id]["filename"]

    # Parse new tags
    new_tags = {}
    for line in text.split('\n'):
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            if "title" in key:
                new_tags['title'] = val
            elif "artist" in key:
                new_tags['artist'] = val
            elif "album" in key:
                new_tags['album'] = val

    # Edit Tags
    try:
        audio = ID3(file_path)
    except Exception:
        audio = ID3()

    if 'title' in new_tags:
        audio["TIT2"] = TIT2(encoding=3, text=new_tags['title'])
    if 'artist' in new_tags:
        audio["TPE1"] = TPE1(encoding=3, text=new_tags['artist'])
    if 'album' in new_tags:
        audio["TALB"] = TALB(encoding=3, text=new_tags['album'])

    audio.save(file_path)

    # Send edited file back
    await update.message.reply_document(
        document=open(file_path, 'rb'),
        caption="🎧 Here is your updated audio file!"
    )
    
    # Clean up state
    del user_states[user_id]
    os.remove(file_path)

# Main Application handler (Required for Telegram Bot API)
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def webhook(request):
    if request.method == "POST":
        req_body = await request.json()
        update = Update.de_json(req_body, bot)
        await application.process_update(update)
        return json.dumps({"status": "ok"})
    return json.dumps({"status": "get not allowed"})
