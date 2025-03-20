import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from client import generate_session

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))

(STATE_API_ID, STATE_API_HASH, STATE_PHONE, STATE_OTP, STATE_2FA) = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "Use /genstring to generate your Telegram String Session."
    )

async def gen_string(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let's start generating your string session!\n\n"
        "Please send your API_ID:"
    )
    return STATE_API_ID

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Process cancelled.")
    return ConversationHandler.END

async def handle_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        api_id = int(update.message.text)
        context.user_data['api_id'] = api_id
        await update.message.reply_text("Great! Now send your API_HASH:")
        return STATE_API_HASH
    except ValueError:
        await update.message.reply_text("Invalid API_ID. Please enter a valid integer.")
        return STATE_API_ID

async def handle_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_hash = update.message.text
    context.user_data['api_hash'] = api_hash
    await update.message.reply_text("Now send your phone number (with country code):")
    return STATE_PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    context.user_data['phone'] = phone
    try:
        string_session = await generate_session(
            api_id=context.user_data['api_id'],
            api_hash=context.user_data['api_hash'],
            phone=phone,
            bot=update.message.bot,
            user_id=update.effective_user.id
        )
        await update.message.reply_text("✅ String session generated successfully! Check your Saved Messages.")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
        return ConversationHandler.END

async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ You are not authorized to use this command.")
        return
    
    await update.message.reply_text("Updating bot from GitHub...")
    try:
        from git import Repo
        repo = Repo('.')
        repo.remotes.origin.pull()
        await update.message.reply_text("✅ Bot updated successfully! Restarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        await update.message.reply_text(f"Update failed: {str(e)}")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('genstring', gen_string)],
        states={
            STATE_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_id)],
            STATE_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_hash)],
            STATE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('updatebot', update_bot))

    application.run_polling()

if __name__ == '__main__':
    main()
