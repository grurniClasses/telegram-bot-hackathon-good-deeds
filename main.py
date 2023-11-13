from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from telegram_bot import MyBot
from data_manager import DataBase
from bot_settings import TOKEN


def main():
    token = TOKEN
    data_manager = DataBase(db='GoodDeeds', users_collection='users', requests_collection='help_requests')
    my_bot = MyBot(token, data_manager)

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', my_bot.start), CommandHandler("menu", my_bot.show_menu)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, my_bot.ask_name)],
            2: [CallbackQueryHandler(my_bot.choose_location)],
            3: [CallbackQueryHandler(my_bot.volunteer_request)],
            4: [MessageHandler(Filters.text & ~Filters.command, my_bot.describe_request)],
            5: [CallbackQueryHandler(my_bot.confirm_edit_request)],
            6: [CallbackQueryHandler(my_bot.chose_menu, pattern="^main")]
        },
        fallbacks=[],
    )

    my_bot.dispatcher.add_handler(conversation_handler)
    # my_bot.dispatcher.add_handler(CommandHandler("menu", my_bot.show_menu))
    # my_bot.dispatcher.add_handler(CallbackQueryHandler(my_bot.chose_menu, pattern="^main"))
    my_bot.updater.start_polling()
    my_bot.updater.idle()


if __name__ == '__main__':
    main()
