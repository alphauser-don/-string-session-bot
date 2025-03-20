from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

async def generate_session(api_id, api_hash, phone, bot, user_id):
    client = Client(":memory:", api_id=api_id, api_hash=api_hash)
    
    await client.connect()
    
    sent_code = await client.send_code(phone)
    
    async def send_code_to_user():
        await bot.send_message(
            chat_id=user_id,
            text=f"Your login code: {sent_code.phone_code_hash}"
        )
    
    await send_code_to_user()
    
    code = input("Enter the OTP: ")  # In real implementation, use conversation handler
    
    try:
        await client.sign_in(phone, sent_code.phone_code_hash, code)
    except SessionPasswordNeeded:
        password = input("Enter your 2FA password: ")  # Add conversation handler step
        await client.check_password(password)
    
    string_session = await client.export_session_string()
    
    await client.send_message("me", f"**String Session:**\n`{string_session}`")
    await client.disconnect()
    
    return string_session
