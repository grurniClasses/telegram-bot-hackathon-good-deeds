import enum
import logging
from typing import Optional

import telegram
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

import telegram_consts
from data_manager import Database

logging.basicConfig(
    format="[%(levelname)s %(asctime)s %(module)s:%(lineno)d] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class MenuOption(enum.Enum):
    ASK_NAME = 1
    CHOOSE_LOCATION = 2
    VOLUNTEER_REQUEST = 3
    DESCRIBE_REQUEST = 4
    CONFIRM_EDIT_REQUEST = 5
    CHOOSE_MENU = 6


class MenuKeyboardOption(enum.Enum):
    NEW_REQUEST = "MENU_OPTION__NEW_REQUEST"
    MY_REQUEST = "MENU_OPTION__MY_REQUEST"
    ALL_REQUEST = "MENU_OPTION__ALL_REQUEST"
    OPEN_REQUEST_BY_LOCATION = "MENU_OPTION__OPEN_REQUEST_BY_LOCATION"
    CHANGE_STATUS = "MENU_OPTION__CHANGE_STATUS"


class VolunteerRequestOption(enum.Enum):
    VOLUNTEER = "VOLUNTEER_REQUEST_OPTION__VOLUNTEER"
    HELP_REQUEST = "VOLUNTEER_REQUEST_OPTION__HELP_REQUEST"


class ConfirmOption(enum.Enum):
    CONFIRM = "CONFIRM_OPTION__CONFIRM"
    EDIT = "CONFIRM_OPTION__EDIT"


class TelegramBot:
    def __init__(self, token, database: Database):
        self._database = database
        self._updater = Updater(token, use_context=True)

    def run(self):
        self._updater.dispatcher.add_handler(ConversationHandler(
            entry_points=[CommandHandler("start", self._start), CommandHandler("menu", self._show_menu)],
            states={
                MenuOption.ASK_NAME.value: [MessageHandler(Filters.text & ~Filters.command, self._ask_name)],
                MenuOption.CHOOSE_LOCATION.value: [CallbackQueryHandler(self._choose_location)],
                MenuOption.VOLUNTEER_REQUEST.value: [CallbackQueryHandler(self._volunteer_request)],
                MenuOption.DESCRIBE_REQUEST.value: [
                    MessageHandler(Filters.text & ~Filters.command, self._describe_request)],
                MenuOption.CONFIRM_EDIT_REQUEST.value: [CallbackQueryHandler(self._confirm_edit_request)],
                MenuOption.CHOOSE_MENU.value: [CallbackQueryHandler(self._choose_menu)]
            },
            fallbacks=[],
        ))

        self._updater.start_polling()
        self._updater.idle()

    def _start(self, update: telegram.Update, context: CallbackContext) -> Optional[int]:
        """checks if user have username, send welcome msg for new user"""
        user_id = update.message.from_user.id
        logger.info(f"> Start chat #{user_id}")
        context.user_data["user_id"] = user_id
        logger.info("fuck")
        if not update.message.from_user.username:
            logger.info(f"user {user_id} has no username")
            context.bot.send_message(user_id, telegram_consts.ERROR_USERNAME)
            return

        update.message.reply_text(telegram_consts.HELLO_MSG, reply_markup=telegram.ReplyKeyboardRemove())

        is_user_exists = self._database.is_user_exists(user_id)
        logger.info(f"> user exist: #{is_user_exists}")
        if not is_user_exists:
            context.bot.send_message(user_id, telegram_consts.DESCRIPTION)
            context.bot.send_message(user_id, telegram_consts.ASK_NAME)
            return MenuOption.ASK_NAME.value

        return self._show_menu(update, context)

    def _ask_name(self, update: telegram.Update, context: CallbackContext) -> int:
        """ask user's name -> shows location keyboard"""
        name = update.message.text
        logger.info(f"> ask name, chat #{update.effective_chat.id}, {name=}")
        context.user_data["name"] = name
        update.message.reply_text(telegram_consts.ASK_LOCATION.format(name), reply_markup=self._get_location_keyboard())
        return MenuOption.CHOOSE_LOCATION.value

    def _choose_location(self, update: telegram.Update, context: CallbackContext) -> int:
        """saves user's location -> ask kind of activity with keyboard"""
        query = update.callback_query
        location = query.data
        logger.info(f"Got location {location}")
        query.answer()
        context.user_data["location"] = location
        query.edit_message_text(telegram_consts.LOCATION_SELECT.format(location))
        chat_id = update.effective_chat.id
        context.bot.send_message(chat_id, telegram_consts.USER_TYPE,
                                 reply_markup=self._get_volunteer_request_keyboard())
        return MenuOption.VOLUNTEER_REQUEST.value

    def _volunteer_request(
            self,
            update: telegram.Update,
            context: CallbackContext,
    ) -> int:
        """saves user's info to db -> send explanation msg or ask to fill in help request"""
        username = update.effective_chat.username
        user_id = update.effective_chat.id
        context.user_data["username"] = username
        self._database.insert_user_info(user_id, username, context.user_data["name"], context.user_data["location"])
        logger.info("user added to database")

        query = update.callback_query
        volunteer_ans = query.data
        logger.info(f"chose: {volunteer_ans}")
        query.answer()
        if volunteer_ans == VolunteerRequestOption.VOLUNTEER.value:
            self._database.update_volunteer_status(user_id)
            if self._database.is_active_user(user_id):
                query.edit_message_text(telegram_consts.VOLUNTEER_MSG)
            return ConversationHandler.END

        query.edit_message_text(telegram_consts.HELP_REQUEST_MSG)
        return MenuOption.DESCRIBE_REQUEST.value

    def _describe_request(self, update: telegram.Update, context: CallbackContext) -> int:
        """checks for correctness of request text"""
        context.user_data["request_text"] = update.message.text
        update.message.reply_text(
            telegram_consts.CONFIRM_REQUEST_MSG.format(context.user_data["request_text"]),
            reply_markup=self._get_confirm_keyboard(),
        )
        return MenuOption.CONFIRM_EDIT_REQUEST.value

    def _confirm_edit_request(
            self,
            update: telegram.Update,
            context: CallbackContext,
    ) -> int:
        """saves a help request to db"""
        user_id = update.callback_query.from_user.id
        user_data = self._database.get_user_data(user_id)
        user_name = user_data.get("username")

        query = update.callback_query
        query.answer()
        choice = query.data

        if choice == ConfirmOption.CONFIRM.value:
            self._database.add_request(
                user_id,
                user_name,
                text=context.user_data["request_text"],
                location=user_data.get("location"),
            )
            logger.info("help request confirmed and saved")
            query.edit_message_text(telegram_consts.CONFIRMED_REQUEST_MSG)
            for active_volunteer in self._database.get_all_active_volunteers():
                logger.info(active_volunteer)
                if active_volunteer.get("user_id") != user_id:
                    context.bot.send_message(
                        active_volunteer.get("user_id"),
                        telegram_consts.REQUEST_HELP_MSG.format(user_name, context.user_data["request_text"]),
                    )
            return ConversationHandler.END

        query.edit_message_text(telegram_consts.EDIT_MSG)
        return MenuOption.DESCRIBE_REQUEST.value

    def _show_menu(self, update: telegram.Update, context: CallbackContext) -> Optional[int]:
        """shows a menu keyboard for authorized users"""
        user_id = update.message.from_user.id
        if not update.message.from_user.username:
            logger.info(f"user {user_id} has no username")
            context.bot.send_message(user_id, telegram_consts.ERROR_USERNAME)
            return

        is_user_exists = self._database.is_user_exists(user_id)
        logger.info(is_user_exists)
        if not is_user_exists:
            logger.info(f"> user exist: #{is_user_exists}")
            context.bot.send_message(user_id, telegram_consts.DESCRIPTION)
            context.bot.send_message(user_id, telegram_consts.ASK_NAME)
            return MenuOption.ASK_NAME.value

        update.message.reply_text(telegram_consts.START_MENU_MSG, reply_markup=self._get_menu_keyboard())
        return MenuOption.CHOOSE_MENU.value

    def _choose_menu(
            self,
            update: telegram.Update,
            context: CallbackContext,
    ) -> int:
        """call for clicked button's func"""
        query = update.callback_query
        query.answer()
        choice = query.data
        user_id = update.callback_query.from_user.id
        logger.info(f"entered chose menu, {choice=}")

        if choice == MenuKeyboardOption.NEW_REQUEST.value:
            # open help request
            query.edit_message_text(telegram_consts.HELP_REQUEST_MSG)
            return MenuOption.DESCRIBE_REQUEST.value

        if choice == MenuKeyboardOption.MY_REQUEST.value:
            query.edit_message_text(telegram_consts.MY_REQUEST)
            for req in self._database.get_user_requests(user_id):
                context.bot.send_message(user_id, req.get("text"))
            return ConversationHandler.END

        if choice == MenuKeyboardOption.ALL_REQUEST.value:
            query.edit_message_text(telegram_consts.OPENED_REQUEST)
            for req in self._database.get_all_active_requests():
                if req.get("user_id") != user_id:
                    context.bot.send_message(
                        user_id,
                        telegram_consts.FULL_REQUEST_MSG.format(
                            req.get("username"),
                            req.get("location"),
                            req.get("text"),
                        ),
                    )
            return ConversationHandler.END

        if choice == MenuKeyboardOption.OPEN_REQUEST_BY_LOCATION.value:
            query.edit_message_text(telegram_consts.OPENED_REQUEST_BY_LOCATION)
            lst_help_requests_by_user_location = self._database.get_local_requests_by_user_location(user_id)
            for request in lst_help_requests_by_user_location:
                if request.get("user_id") != user_id:
                    context.bot.send_message(
                        user_id,
                        telegram_consts.REQUEST_HELP_MSG.format(request.get("username"), request.get("text")),
                    )
            return ConversationHandler.END

        if choice == MenuKeyboardOption.CHANGE_STATUS.value:
            self._database.update_volunteer_status(user_id)
            if self._database.is_active_user(user_id):
                query.edit_message_text(telegram_consts.ADDED_TO_VOLUNTEER_LIST)
            else:
                query.edit_message_text(telegram_consts.REMOVED_FROM_VOLUNTEERS)

        return ConversationHandler.END

    @staticmethod
    def _get_location_keyboard() -> telegram.InlineKeyboardMarkup:
        """creates keyboard for choosing location"""
        return telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton(telegram_consts.SOUTH, callback_data=telegram_consts.SOUTH),
                telegram.InlineKeyboardButton(telegram_consts.CENTER, callback_data=telegram_consts.CENTER),
            ],
            [telegram.InlineKeyboardButton(telegram_consts.NORTH, callback_data=telegram_consts.NORTH)],
        ])

    @staticmethod
    def _get_volunteer_request_keyboard() -> telegram.InlineKeyboardMarkup:
        """creates keyboard for choosing kind of activity"""
        return telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton(
                telegram_consts.TO_VOLUNTEER,
                callback_data=VolunteerRequestOption.VOLUNTEER.value,
            ),
            telegram.InlineKeyboardButton(
                telegram_consts.TO_HELP_REQUEST,
                callback_data=VolunteerRequestOption.HELP_REQUEST.value,
            ),
        ]])

    @staticmethod
    def _get_confirm_keyboard() -> telegram.InlineKeyboardMarkup:
        """creates keyboard for processing text of help request"""
        return telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton(telegram_consts.EDIT, callback_data=ConfirmOption.EDIT.value),
            telegram.InlineKeyboardButton(telegram_consts.CONFIRM, callback_data=ConfirmOption.CONFIRM.value),
        ]])

    @staticmethod
    def _get_menu_keyboard() -> telegram.InlineKeyboardMarkup:
        """creates keyboard for main menu"""
        return telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton(
                    telegram_consts.NEW_REQUEST,
                    callback_data=MenuKeyboardOption.NEW_REQUEST.value,
                ),
                telegram.InlineKeyboardButton(
                    telegram_consts.MY_REQUEST,
                    callback_data=MenuKeyboardOption.MY_REQUEST.value,
                ),
            ],
            [
                telegram.InlineKeyboardButton(
                    telegram_consts.ALL_REQUEST,
                    callback_data=MenuKeyboardOption.ALL_REQUEST.value,
                ),
                telegram.InlineKeyboardButton(
                    telegram_consts.OPEN_REQUEST_BY_LOCATION,
                    callback_data=MenuKeyboardOption.OPEN_REQUEST_BY_LOCATION.value,
                ),
            ],
            [telegram.InlineKeyboardButton(
                telegram_consts.CHANGE_STATUS,
                callback_data=MenuKeyboardOption.CHANGE_STATUS.value,
            )],
        ])
