import os
import logging
import sys
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from pyrogram.errors import SessionPasswordNeeded
from client import create_client

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))

# Conversation states
(STATE_API_ID, STATE_API_HASH, STATE_PHONE, STATE_OTP, STATE_2FA) = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "Use /genstring to generate your Telegram String Session."
    )

async def gen_string(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let's generate your string session!\n\n"
        "Please send your API_ID:"
    )
    return STATE_API_ID

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Process cancelled.")
    return ConversationHandler.END

async def handle_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        api_id = int(update.message.text)
        context.user_data['api_id'] = api_id
        await update.message.reply_text("✅ API_ID accepted! Now send your API_HASH:")
        return STATE_API_HASH
    except ValueError:
        await update.message.reply_text("❌ Invalid API_ID. Please enter a valid integer.")
        return STATE_API_ID

async def handle_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['api_hash'] = update.message.text
    await update.message.reply_text("📱 Now send your phone number (with country code):\nExample: +14151234567")
    return STATE_PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    try:
        client = await create_client(
            api_id=context.user_data['api_id'],
            api_hash=context.user_data['api_hash'],
            session_name=str(update.effective_user.id)
        )
        await client.connect()
        sent_code = await client.send_code(context.user_data['phone'])
        context.user_data['client'] = client
        context.user_data['phone_code_hash'] = sent_code.phone_code_hash
        
        await update.message.reply_text("🔢 OTP sent to your Telegram account! Enter the code:")
        return STATE_OTP
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['otp'] = update.message.text.replace(" ", "")
    client = context.user_data['client']
    
    try:
        await client.sign_in(
            phone_number=context.user_data['phone'],
            phone_code_hash=context.user_data['phone_code_hash'],
            phone_code=context.user_data['otp']
        )
    except SessionPasswordNeeded:
        await update.message.reply_text("🔑 Enter your 2FA password:")
        return STATE_2FA
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return await cleanup_session(context)
    
    return await finalize_session(update, context)

async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['2fa_password'] = update.message.text
    client = context.user_data['client']
    
    try:
        await client.check_password(context.user_data['2fa_password'])
        return await finalize_session(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ 2FA Failed: {str(e)}")
        return await cleanup_session(context)

async def finalize_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data['client']
    string_session = await client.export_session_string()
    
    try:
        await client.send_message("me", f"**Your String Session:**\n`{string_session}`")
        await update.message.reply_text("✅ Success! Check your Saved Messages.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Session generated but couldn't send to Saved Messages:\n`{string_session}`")
    
    await client.disconnect()
    return ConversationHandler.END

async def cleanup_session(context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('client')
    if client:
        await client.disconnect()
    return ConversationHandler.END

async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔️ Unauthorized!")
        return
    
    await update.message.reply_text("🔄 Updating from GitHub...")
    try:
        from git import Repo
        repo = Repo('.')
        origin = repo.remotes.origin
        origin.pull()
        await update.message.reply_text("✅ Update successful! Restarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        await update.message.reply_text(f"❌ Update failed: {str(e)}")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('genstring', gen_string)],
        states={
            STATE_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_id)],
            STATE_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_hash)],
            STATE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            STATE_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
            STATE_2FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_2fa)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('updatebot', update_bot))

    application.run_polling()

if __name__ == '__main__':
    main()
