"""Telegram notifications."""
import aiohttp

class TelegramClient:
    def __init__(self, bot_token: str, admin_chat_id: str):
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    async def send_message(self, chat_id: str, text: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/sendMessage", json={"chat_id": chat_id, "text": text}) as resp:
                    return (await resp.json()).get("ok", False)
        except:
            return False
    async def notify_admin(self, text: str) -> bool:
        return await self.send_message(self.admin_chat_id, text)
