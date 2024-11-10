import asyncio
import logging

import uvicorn
from asgiref.wsgi import WsgiToAsgi

from . import app, bot
from .settings import settings

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def run_bot() -> None:
    """Run the bot setup."""
    try:
        # Закомментировать bot.bot.set_webhook, если нет ТГ токена
        await bot.bot.set_webhook(
            url=settings.WEBHOOK_URL,
            allowed_updates=bot.dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logger.info('Бот запущен')
    except Exception as e:
        logger.error(f'Error setting up bot: {e}')


async def run_webserver() -> None:
    """Run the web server."""
    config = uvicorn.Config(
        app=WsgiToAsgi(app),
        port=settings.PORT,
        use_colors=False,
        host='0.0.0.0',
        workers=2,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    """Стартуем сервер и бота."""
    logger.info('Starting main function')

    # Create tasks for bot and webserver
    bot_task = asyncio.create_task(run_bot())
    webserver_task = asyncio.create_task(run_webserver())

    # Wait for both tasks to complete
    await asyncio.gather(bot_task, webserver_task)

    # Close the bot session
    await bot.bot.session.close()

    logger.info('Main function completed')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error('Бот остановлен')
    except Exception as e:
        logger.exception(f'An unexpected error occurred: {e}')
