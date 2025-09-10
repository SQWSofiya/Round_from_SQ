import os
import subprocess
import uuid
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

REQUIRED_CHANNEL = "@sqw_factory"

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video = update.message.video

    if not await is_user_subscribed(user.id, context):
        await update.message.reply_text(
            f"Пожалуйста, подпишитесь на канал {REQUIRED_CHANNEL}, чтобы пользоваться ботом 😊"
        )
        return

    file = await video.get_file()
    input_path = f"{uuid.uuid4()}.mp4"
    output_path = f"{uuid.uuid4()}.mp4"

    await file.download_to_drive(input_path)

    subprocess.run([
        "ffmpeg", "-i", input_path,
        "-vf", "scale=256:256:force_original_aspect_ratio=decrease,pad=256:256:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-t", "60", "-an", "-y", output_path
    ])

    with open(output_path, "rb") as video_note:
        await update.message.reply_video_note(video_note)

    os.remove(input_path)
    os.remove(output_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    
    import threading
    import http.server
    import socketserver

    def run_dummy_server():
        port = int(os.environ.get('PORT', 10000))
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()

    main()


