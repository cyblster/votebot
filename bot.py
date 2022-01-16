import os
import telebot
import pymysql
import logging

from flask import Flask, request
from telebot import types
from datetime import datetime, timedelta, timezone


APP_URL = os.environ.get("app_url")
APP_TOKEN = os.environ.get("app_token")

MYSQL_HOST = os.environ.get("mysql_host")
MYSQL_USER = os.environ.get("mysql_user")
MYSQL_PASSWORD = os.environ.get("mysql_password")
MYSQL_DATABASE = os.environ.get("mysql_database")

MENU_TEXT = "<b>[Меню] ({timestamp})</b>\n\n" \
             "<b>Вопрос:</b> {question}\n" \
             "<b>Вариант А:</b> {answer_a}\n" \
             "<b>Вариант Б:</b> {answer_b}\n\n" \
             "<b>Активен:</b> {is_active}"

SETTINGS_TEXT = "<b>[Настройки голосования] ({timestamp})</b>\n\n" \
                "{text}"

setting_question_is_active = False
setting_answer_a_is_active = False
setting_answer_b_is_active = False

owner_inline_keyboard = types.InlineKeyboardMarkup()
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Обновить", callback_data="refresh"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Настройки голосования", callback_data="settings"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Начать голосование", callback_data="vote_start"))

settings_inline_keyboard = types.InlineKeyboardMarkup()
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Вопрос", callback_data="settings_question"))
settings_inline_keyboard.add(
    types.InlineKeyboardButton(text="Вариант А", callback_data="settings_answer_a"),
    types.InlineKeyboardButton(text="Вариант Б", callback_data="settings_answer_b")
)
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data="back"))

member_inline_keyboard = types.InlineKeyboardMarkup()
member_inline_keyboard.add(
    types.InlineKeyboardButton(text="Вариант А", callback_data="vote_answer_a"),
    types.InlineKeyboardButton(text="Вариант Б", callback_data="vote_answer_b"),
)
member_inline_keyboard.add(types.InlineKeyboardButton(text="Результаты", url=APP_URL, callback_data="vote_result"))

owner_list = []
with pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DATABASE) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM `owner`")
        for fetch in cursor.fetchall():
            telegram_id, telegram_username, telegram_firstname, telegram_lastname = fetch[:4]
            owner_list.append({
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
                "telegram_firstname": telegram_firstname,
                "telegram_lastname": telegram_lastname
            })

member_list = []
with pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DATABASE) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM `member`")
        for fetch in cursor.fetchall():
            telegram_id, telegram_username, telegram_firstname, telegram_lastname = fetch[:4]
            member_list.append({
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
                "telegram_firstname": telegram_firstname,
                "telegram_lastname": telegram_lastname
            })

server = Flask(__name__)
bot = telebot.TeleBot(token=APP_TOKEN)

logger = telebot.logger
logger.setLevel(logging.DEBUG)


# website
# =================================================================================================================

@server.route("/")
def vote_result():
    result = "<h1>Результаты</h1>"

    return result, 200


# telegram
# =================================================================================================================

@server.route(f"/{APP_TOKEN}", methods=["POST"])
def bot_webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


@bot.message_handler(commands=["start"], chat_types=["private"])
def command_start(message):
    if message.from_user.id in [owner["telegram_id"] for owner in owner_list]:
        with pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DATABASE) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM `system`")
                fetch = cursor.fetchall()

                _id, question, answer_a, answer_b, is_active = fetch[0][:5]
                bot.send_message(
                    chat_id=message.from_user.id,
                    text=MENU_TEXT.format(
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        question=question if question else "Отсутствует",
                        answer_a=answer_a if answer_a else "Отсутствует",
                        answer_b=answer_b if answer_b else "Отсутствует",
                        is_active="Да" if is_active else "Нет"
                    ),
                    parse_mode="HTML",
                    reply_markup=owner_inline_keyboard,
                )

    elif message.from_user.id in [member["telegram_id"] for member in member_list]:
        bot.send_message(
            chat_id=message.from_user.id,
            text="Вы уже зарегистрировались! Ожидайте начала."
        )

    else:
        pass


@bot.message_handler(content_types=["text"], chat_types=["private"])
def message_any(message):
    if message.from_user.id in [owner["telegram_id"] for owner in owner_list]:
        if setting_question_is_active:
            with pymysql.connect(
                    host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                    db=MYSQL_DATABASE, autocommit=True
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"UPDATE `system` SET question = '{message.text}' WHERE id = '1'")

            bot.send_message(
                chat_id=message.from_user.id,
                text=SETTINGS_TEXT.format(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    text="Текст вопроса был успешно изменен."
                ),
                parse_mode="HTML",
                reply_markup=owner_inline_keyboard
            )

        elif setting_answer_a_is_active:
            with pymysql.connect(
                    host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                    db=MYSQL_DATABASE, autocommit=True
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"UPDATE `system` SET answer_a = '{message.text}' WHERE id = '1'")

            bot.send_message(
                chat_id=message.from_user.id,
                text=SETTINGS_TEXT.format(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    text="Текст ответа А был успешно изменен."
                ),
                parse_mode="HTML",
                reply_markup=owner_inline_keyboard
            )

        elif setting_answer_b_is_active:
            with pymysql.connect(
                    host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                    db=MYSQL_DATABASE, autocommit=True
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"UPDATE `system` SET answer_b = '{message.text}' WHERE id = '1'")

            bot.send_message(
                chat_id=message.from_user.id,
                text=SETTINGS_TEXT.format(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    text="Текст ответа Б был успешно изменен."
                ),
                parse_mode="HTML",
                reply_markup=owner_inline_keyboard
            )


@bot.callback_query_handler(lambda call: True)
def handler_query(call):
    global setting_question_is_active
    global setting_answer_a_is_active
    global setting_answer_b_is_active

    if call.data in ["refresh", "back"]:
        setting_question_is_active = False
        setting_answer_a_is_active = False
        setting_answer_b_is_active = False

        with pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DATABASE) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM `system`")
                fetch = cursor.fetchall()

                question, answer_a, answer_b, is_active = fetch[0][1:5]
                bot.edit_message_text(
                    chat_id=call.from_user.id,
                    message_id=call.message.message_id,
                    text=MENU_TEXT.format(
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        question=question if question else "Отсутствует",
                        answer_a=answer_a if answer_a else "Отсутствует",
                        answer_b=answer_b if answer_b else "Отсутствует",
                        is_active="Да" if is_active else "Нет"
                    ),
                    parse_mode="HTML",
                    reply_markup=owner_inline_keyboard,
                )

    elif call.data == "settings":
        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=SETTINGS_TEXT.format(
                text="Выберите пункт, который хотите изменить:",
                timestamp=datetime.now().strftime("%H:%M:%S")
            ),
            parse_mode="HTML",
            reply_markup=settings_inline_keyboard
        )

    elif call.data == "settings_question":
        setting_question_is_active = True
        setting_answer_a_is_active = False
        setting_answer_b_is_active = False

        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=SETTINGS_TEXT.format(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                text="Напишите текст вопроса:"
            ),
            parse_mode="HTML",
            reply_markup=owner_inline_keyboard
        )

    elif call.data == "settings_answer_a":
        setting_question_is_active = False
        setting_answer_a_is_active = True
        setting_answer_b_is_active = False

        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=SETTINGS_TEXT.format(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                text="Напишите текст ответа А:"
            ),
            parse_mode="HTML",
            reply_markup=owner_inline_keyboard
        )

    elif call.data == "settings_answer_b":
        setting_question_is_active = False
        setting_answer_a_is_active = False
        setting_answer_b_is_active = True

        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=SETTINGS_TEXT.format(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                text="Напишите текст ответа Б:"
            ),
            parse_mode="HTML",
            reply_markup=owner_inline_keyboard
        )

    elif call.data == "vote_start":
        pass


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL + APP_TOKEN)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
