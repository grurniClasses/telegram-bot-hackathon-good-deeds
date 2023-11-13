import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram import Update
from telegram.ext import Updater, CallbackContext, ConversationHandler

from data_manager import DataBase  # ?? for typing

HELLO_MSG = "💐תודה שבחרת להפיץ אור ולהפוך את העולם למקום טוב יותר"
DESCRIPTION = (
    "ברוכים הבאים לבוט המעשים הטובים!\n אז איך הבוט שלנו פועל: ניתן להיכנס כמתנדבים, שם תקבלו הודעות על בקשות "
    "מקומיות לעזרה.\n לחילופין, אם אתם צריכים סיוע, אתם יכולים לפרסם בקשה שתגיע לצוות "
    "המתנדבים המסור שלנו שמוכן להשפיע לטובה.\n בין אם אתם כאן כדי לתת יד או מחפשים סיוע, מעשים טובים היא "
    "הפלטפורמה שלכם לטיפוח חסד קהילתי.")
ASK_NAME = "מהו שמך?✏"
ASK_LOCATION = "נעים להכיר אותך {},\nמהו מיקומך?"
USER_TYPE = "להושיט יד או לחפש תמיכה, הבחירה לגמרי בידך - מעשים טובים כאן עבור כולם"
VOLUNTEER_MSG = ("תודה שבחרת להיות מגדלור של חסד בקהילה שלנו! ההחלטה שלך להתנדב מעידה רבות על החמלה והנכונות שלך "
                 "להשפיע על העולם שלנו ולהפוך אותו למקום טוב יותר.")
HELP_REQUEST_MSG = "איך המתנדבים שלנו יוכלו לסייע לך היום?"
CONFIRM_REQUEST_MSG = "האם לשנות את נוסח הבקשה?:\n\n{}"
CONFIRMED_REQUEST_MSG = ("הבקשה התקבלה ונשלחת ברגעים אלו לצוות המתנדבים המסורים שלנו, מתנדב מאזורך שיוכל לעזור יצור "
                         "איתך קשר בהקדם, תודה!")
START_MENU_MSG = "Chose: "

logging.basicConfig(
    format="[%(levelname)s %(asctime)s %(module)s:%(lineno)d] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


class MyBot:
    def __init__(self, token, database: DataBase):
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.database = database

    def start(self, update: Update, context: CallbackContext):
        user_id = update.message.from_user.id
        context.user_data['user_id'] = user_id
        update.message.reply_text(HELLO_MSG, reply_markup=ReplyKeyboardRemove())
        logger.info(f"> Start chat #{user_id}")
        logger.info(f"> user exist: #{self.database.is_user(user_id)}")
        if not self.database.is_user(user_id):
            logger.info(f"> user exist: #{self.database.is_user(user_id)}")
            context.bot.send_message(chat_id=user_id,
                                     text=DESCRIPTION)
            context.bot.send_message(chat_id=user_id, text=ASK_NAME)
            return 1
        return self.show_menu(update, context)

    def ask_name(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        name = update.message.text
        logger.info(f"> ask name, chat #{chat_id}, {name=}")
        context.user_data['name'] = name
        update.message.reply_text(ASK_LOCATION.format(name),
                                  reply_markup=self.get_location_keyboard())
        return 2

    def choose_location(self, update: Update, context: CallbackContext):
        query = update.callback_query
        logger.info(f"Got location {query.data}")
        location = query.data
        query.answer()
        context.user_data['location'] = location
        query.edit_message_text(f"בחרת {location}")
        chat_id = update.effective_chat.id
        context.bot.send_message(chat_id=chat_id,
                                 text=USER_TYPE, reply_markup=self.get_volunteer_request_keyboard())
        return 3

    def volunteer_request(self, update: Update, context: CallbackContext):
        query = update.callback_query
        logger.info(f"chose  {query.data}")
        query.answer()
        volunteer_ans = query.data
        query.edit_message_text(f"בחרת {volunteer_ans}")
        username = update.effective_chat.username
        context.user_data["username"] = username
        self.database.upsert_user_info(context.user_data['user_id'], username, context.user_data['name'],
                                       context.user_data['location'])
        logger.info("user added to database")

        if volunteer_ans == "volunteer":
            self.database.update_volunteer_status(context.user_data['user_id'])
            query.edit_message_text(VOLUNTEER_MSG)
            return ConversationHandler.END

        elif volunteer_ans == "help_request":
            query.edit_message_text(HELP_REQUEST_MSG)
            return 4

    def describe_request(self, update: Update, context: CallbackContext):
        context.user_data['request_text'] = update.message.text
        update.message.reply_text(CONFIRM_REQUEST_MSG.format(context.user_data['request_text']),
                                  reply_markup=self.get_confirm_edit_keyboard())
        return 5

    def confirm_edit_request(self, update: Update, context: CallbackContext):
        user_id = update.callback_query.from_user.id
        location = self.database.get_user_data(user_id).get("location")
        logger.info(location)
        user_name = self.database.get_user_data(user_id).get("username")
        chat_id = update.effective_chat.id

        query = update.callback_query

        query.answer()
        choice = query.data

        if choice == "confirm":

            self.database.add_request(user_id,
                                      text=context.user_data['request_text'],
                                      location=location)
            logger.info("help request confirmed and saved")
            query.edit_message_text(CONFIRMED_REQUEST_MSG)
            for active_volunteer in self.database.get_all_active_volunteers():
                context.bot.send_message(chat_id=active_volunteer.get("id_user"),
                                         text=f"@{user_name} צריך עזרה ל: \n{context.user_data['request_text']}")
                # context.bot.send_contact(chat_id=active_volunteer.get("user_id"), )
            return ConversationHandler.END
        elif choice == "edit":
            query.edit_message_text("נסחו מחדש את הבקשה:")
            return 4

    def show_menu(self, update: Update, context: CallbackContext):
        update.message.reply_text(START_MENU_MSG,
                                  reply_markup=self.get_menu_keyboard())
        return 6

    def chose_menu(self, update: Update, context: CallbackContext):
        query = update.callback_query
        logger.info(f"entered chose menu, {query=}")

        user_id = update.message.from_user.id
        query.answer()
        choice = query.data

        if choice == "main_1":
            # open help request
            query.edit_message_text(HELP_REQUEST_MSG)
            return 4
        if choice == "2":
            pass
        if choice == "3":
            pass
        if choice == "main_4":
            lst_help_requests_by_user_location = self.database.get_local_requests_by_user_location()
            for request in lst_help_requests_by_user_location:
                context.bot.send_message(chat_id=user_id,
                                         text=f"@{request.get('user_name')} צריך עזרה ל: \n{request.get('request_text')}")
        if choice == "main_5":
            self.database.update_volunteer_status(user_id)

    @staticmethod
    def get_location_keyboard():
        keyboard = [
            [
                InlineKeyboardButton("דרום", callback_data="south"),
                InlineKeyboardButton("מרכז", callback_data="center"),
            ],
            [InlineKeyboardButton("צפון", callback_data="north")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_volunteer_request_keyboard():
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("להתנדב", callback_data="volunteer"),
            InlineKeyboardButton("לחפש סיוע", callback_data="help_request"),
        ]])

    @staticmethod
    def get_confirm_edit_keyboard():
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("עריכה", callback_data="edit"),
            InlineKeyboardButton("אישור", callback_data="confirm"),
        ]])

    @staticmethod
    def get_menu_keyboard():
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("פתח בקשת עזרה", callback_data="main_1"),
            InlineKeyboardButton("הצג את בקשות העזרה שלי", callback_data="main_2"),
        ],
            [
                InlineKeyboardButton("הצג את כל בקשות העזרה", callback_data="main_3"),
                InlineKeyboardButton("הצג בקשות עזרה במיקום שלי", callback_data="main_4"),
            ],
            [InlineKeyboardButton("שנה סטטוס מתנדב", callback_data="main_5")]
        ])
