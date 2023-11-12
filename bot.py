import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackContext,
    Updater,
)

import bot_settings

WELCOME_TEXT = "Welcome to our bot!"

logging.basicConfig(
    format="[%(levelname)s %(asctime)s %(module)s:%(lineno)d] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    logger.info(f"> Start chat #{chat_id}")
    context.bot.send_message(chat_id=chat_id, text=WELCOME_TEXT)


my_bot = Updater(token=bot_settings.BOT_TOKEN, use_context=True)
my_bot.dispatcher.add_handler(CommandHandler("start", start))

logger.info("* Start polling...")
my_bot.start_polling()  # Starts polling in a background thread.
my_bot.idle()  # Wait until Ctrl+C is pressed
logger.info("* Bye!")
