from bot_settings import TOKEN
from data_manager import Database
from telegram_bot import TelegramBot


def main():
    TelegramBot(TOKEN, Database()).run()


if __name__ == '__main__':
    main()
