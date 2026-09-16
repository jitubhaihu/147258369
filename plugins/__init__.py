from aiohttp import web
from .route import routes
from asyncio import sleep 
from datetime import datetime
from database.users_chats_db import db
from info import URL, PREMIUM_LOGS
from Script import script
import aiohttp
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

async def check_expired_premium(client):
    while True:
        data = await db.get_expired(datetime.now())
        for user in data:
            user_id = user["id"]
            await db.remove_premium_access(user_id)

            # User notification: a blocked/deleted user should not stop the expiry loop.
            try:
                tg_user = await client.get_users(user_id)
                await client.send_message(
                    chat_id=user_id,
                    text=script.PREMIUM_END_TEXT.format(tg_user.mention)
                )
            except Exception as e:
                logging.warning("Premium user notification skipped for %s: %s", user_id, e)

            # Premium log channel is optional. An invalid/missing channel ID must
            # never break premium expiry processing.
            if PREMIUM_LOGS and int(PREMIUM_LOGS) not in (-100, 0):
                try:
                    tg_user = locals().get("tg_user") or await client.get_users(user_id)
                    await client.send_message(
                        chat_id=PREMIUM_LOGS,
                        text=f"<b>#Premium_Expire\n\nUser name: {tg_user.mention}\nUser id: <code>{user_id}</code>"
                    )
                except Exception as e:
                    logging.warning("Premium expiry log skipped for %s: %s", PREMIUM_LOGS, e)

            await sleep(0.5)
        await sleep(1)

async def keep_alive():
    """Keep the Render service alive using its public hostname only."""
    # URL is intentionally empty if Render did not provide a public hostname.
    # Never attempt to connect to 0.0.0.0.
    if not URL or "0.0.0.0" in URL or "127.0.0.1" in URL or "localhost" in URL:
        logging.info("Keep-alive skipped: no valid public URL configured.")
        return

    interval = max(60, int(PING_INTERVAL or 1200))
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            await asyncio.sleep(interval)
            try:
                async with session.get(URL, allow_redirects=True) as resp:
                    if resp.status != 200:
                        logging.warning("⚠️ Ping Error! Status: %s", resp.status)
            except Exception as e:
                logging.warning("⚠️ Ping Failed for %s: %s", URL, e)

