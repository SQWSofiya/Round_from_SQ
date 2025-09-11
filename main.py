import os
import subprocess
import uuid
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from contextlib import suppress

REQUIRED_CHANNEL = "@sqw_factory"

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ Переменная окружения BOT_TOKEN не задана.")

ADMIN_ID = 230479313
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return set()
    try:
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_users(user_ids):
    with open(USERS_FILE, "w") as f:
        json.dump(list(user_ids), f)

async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = load_users()

    if user_id not in users:
        users.add(user_id)
        save_users(users)

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"➕ Новый пользователь. Всего: {len(users)}"
        )

    await update.message.reply_text(
        "👋 Привет! Я превращаю твои видео в кружочки 🎥✨\n\n"
        "🔹 Просто пришли видео (до 60 секунд).\n"
        "🔹 Убедись, что подписан на канал @sqw_factory.\n"
        "🔹 Получишь Telegram-кружок с сохранённым звуком!\n\n"
        "Если что-то не работает — попробуй другое видео или напиши @SQWSofiya 💬"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video = update.message.video

    if video.duration and video.duration > 60:
        await update.message.reply_text("⚠️ Пожалуйста, отправьте видео длиной не более 60 секунд.")
        return

    if not await is_user_subscribed(user.id, context):
        await update.message.reply_text(
            f"Пожалуйста, подпишитесь на канал {REQUIRED_CHANNEL}, чтобы пользоваться ботом 😊"
        )
        return

    processing_message = await update.message.reply_text("⏳ Подождите, ваше видео обрабатывается...")

    input_path = f"{uuid.uuid4()}.mp4"
    output_path = f"{uuid.uuid4()}.mp4"

    try:
        file = await video.get_file()
        await file.download_to_drive(input_path)

        subprocess.run([
            "ffmpeg", "-i", input_path,
            "-vf", "crop='min(in_w\\,in_h)':'min(in_w\\,in_h)',scale=640:640",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-t", "60", "-y", output_path
        ], check=True)

        with open(output_path, "rb") as video_note:
            await update.message.reply_video_note(video_note)

    except subprocess.CalledProcessError as e:
        await update.message.reply_text(
            "⚠️ Не удалось обработать видео. "
            "Проверьте, что оно не повреждено и длится не более 60 секунд."
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "⚠️ Ошибка при обработке видео:\n"
                f"ID: {user.id}\n"
                f"Ошибка: {str(e)}"
            )
        )

    finally:
        with suppress(Exception):
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
        with suppress(Exception):
            os.remove(input_path)
        with suppress(Exception):
            os.remove(output_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    app.run_polling()

if __name__ == "__main__":
    import threading
    import http.server
    import socketserver

    def run_dummy_server():
        port = int(os.environ.get("PORT", 10000))
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()

    main()
