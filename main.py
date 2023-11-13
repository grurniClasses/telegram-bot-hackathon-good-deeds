from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from telegram_bot import MyBot
from data_manager import DataBase
from my_token import TOKEN


def main():
    token = TOKEN
    data_manager = DataBase(db='GoodDeeds', users_collection='users', requests_collection='help_requests')
    my_bot = MyBot(token, data_manager)

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', my_bot.start)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, my_bot.ask_name)],
            2: [CallbackQueryHandler(my_bot.choose_location)],
            3: [CallbackQueryHandler(my_bot.volunteer_request)],
            4: [MessageHandler(Filters.text & ~Filters.command, my_bot.describe_request)],
            5: [CallbackQueryHandler(my_bot.confirm_edit_request)]
        },
        fallbacks=[],
    )

    my_bot.dispatcher.add_handler(conversation_handler)
    my_bot.dispatcher.add_handler(CommandHandler("Menu", my_bot.show_menu))
    my_bot.updater.start_polling()
    my_bot.updater.idle()


if __name__ == '__main__':
    main()
