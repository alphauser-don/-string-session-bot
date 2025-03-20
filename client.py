from pyrogram import Client
from pyrogram.errors import ApiIdInvalid, PhoneNumberInvalid

async def create_client(
    api_id: int, 
    api_hash: str, 
    session_name: str
) -> Client:
    """
    Creates and returns a Pyrogram Client instance with validation
    
    Args:
        api_id: Telegram API ID from my.telegram.org
        api_hash: Telegram API HASH from my.telegram.org
        session_name: Unique identifier for user session
    
    Returns:
        Pyrogram Client instance
    
    Raises:
        ValueError: If credentials are invalid
    """
    try:
        return Client(
            name=str(session_name),
            api_id=api_id,
            api_hash=api_hash,
            workdir="sessions/",
            in_memory=False  # Persist session for error recovery
        )
    except (ApiIdInvalid, PhoneNumberInvalid) as e:
        raise ValueError(f"Invalid credentials: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Client creation failed: {str(e)}") from e
