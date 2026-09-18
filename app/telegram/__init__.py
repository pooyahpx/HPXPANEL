import asyncio
from asyncio import Lock

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app import on_shutdown, on_startup
from app.models.settings import Telegram
from app.nats import is_nats_enabled
from app.settings import telegram_settings
from app.utils.logger import get_logger
from config import nats_settings

from .fsm_storage import NatsFSMStorage
from .handlers import include_routers
from .middlewares import setup_middlewares

logger = get_logger("telegram-bot")


class TelegramBotManager:
    def __init__(self):
        self._bot: Bot | None = None
        self._polling_task: asyncio.Task | None = None
        self._lock = Lock()
        self._dp = self._create_dispatcher()
        self._handlers_registered = False
        self._shutdown_in_progress = False
        self._stop_requested = False
        self._settings_key: tuple | None = None

    @staticmethod
    def _create_dispatcher() -> Dispatcher:
        if is_nats_enabled():
            storage = NatsFSMStorage(nats_settings.telegram_kv_bucket)
            return Dispatcher(storage=storage, events_isolation=storage.create_isolation())
        return Dispatcher(storage=MemoryStorage())

    def get_bot(self) -> Bot | None:
        return self._bot

    def get_dispatcher(self) -> Dispatcher:
        return self._dp

    @staticmethod
    def _settings_key_from_model(settings: Telegram | None) -> tuple | None:
        if not settings:
            return None
        return (
            settings.enable,
            settings.token,
            settings.proxy_url,
        )

    async def sync_from_settings(self, force: bool = False):
        settings: Telegram = await telegram_settings()
        async with self._lock:
            if self._stop_requested:
                return

            new_key = self._settings_key_from_model(settings)
            if not force and new_key == self._settings_key:
                return

            await self._shutdown_locked()

            if settings and settings.enable:
                await self._start_locked(settings)

            self._settings_key = new_key

    async def shutdown(self):
        async with self._lock:
            self._stop_requested = True
            await self._shutdown_locked()
            try:
                await self._dp.fsm.close()
            except Exception:
                pass

    async def _start_long_polling(self):
        retry_period = 30
        logger.info("Starting long polling")
        while True:
            try:
                await self._dp.start_polling(self._bot, handle_signals=False)
                logger.info("Long polling stopped")
                return

            except asyncio.CancelledError:
                logger.info("Long polling task canceled")
                return

            except Exception as err:
                logger.warning(f"Long polling failed: {err}. Retrying in {retry_period} seconds")

            await asyncio.sleep(retry_period)

    async def _start_locked(self, settings: Telegram):
        if is_nats_enabled():
            logger.warning(
                "Telegram long polling is not supported in multi-worker mode, skipping bot start. "
                "Disable NATS and set UVICORN_WORKERS=1."
            )
            return

        logger.info("Telegram bot starting (long polling)")
        proxy = (settings.proxy_url or "").strip() or None
        if proxy and ("example.com" in proxy or "proxy.example" in proxy):
            logger.warning("Ignoring placeholder Telegram proxy_url=%s", proxy)
            proxy = None
        session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
        self._bot = Bot(token=settings.token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

        if not self._handlers_registered:
            try:
                include_routers(self._dp)
                setup_middlewares(self._dp)
                self._handlers_registered = True
            except RuntimeError:
                pass

        # Clear any previously registered Telegram webhook so getUpdates works.
        try:
            await self._bot.delete_webhook(drop_pending_updates=True)
        except Exception as err:
            logger.warning(f"Delete webhook before polling - {err}")

        self._polling_task = asyncio.create_task(self._start_long_polling())

    async def _shutdown_locked(self):
        if self._shutdown_in_progress:
            return
        self._shutdown_in_progress = True
        try:
            if isinstance(self._bot, Bot):
                logger.info("Shutting down telegram bot")
                if self._polling_task is not None:
                    logger.info("Stopping long polling")
                    try:
                        await self._dp.stop_polling()
                    except RuntimeError:
                        pass

                    self._polling_task.cancel()

                if self._bot.session:
                    await self._bot.session.close()

                self._bot = None
                self._polling_task = None
                logger.info("Telegram bot shut down successfully.")
        finally:
            self._shutdown_in_progress = False


telegram_bot_manager = TelegramBotManager()


def get_bot():
    return telegram_bot_manager.get_bot()


def get_dispatcher():
    return telegram_bot_manager.get_dispatcher()


async def startup_telegram_bot():
    await telegram_bot_manager.sync_from_settings(force=True)


async def shutdown_telegram_bot():
    await telegram_bot_manager.shutdown()


on_startup(startup_telegram_bot)
on_shutdown(shutdown_telegram_bot)
