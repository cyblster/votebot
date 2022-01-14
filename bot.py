import os
import pymysql
import logging

from flask import Flask, request
from telebot import TeleBot, types, logger
from datetime import datetime, timedelta, timezone


APP_URL = os.environ.get("app_url")
APP_TOKEN = os.environ.get("app_token")

MYSQL_HOST = os.environ.get("mysql_host")
MYSQL_USER = os.environ.get("mysql_user")
MYSQL_PASSWORD = os.environ.get("mysql_password")
MYSQL_DATABASE = os.environ.get("mysql_database")

OWNER_MENU_TEXT = "Время сейчас: {time_current}\n\n" \
                  "Текущий вопрос: {question_current}\n\n" \
                  "Голосование началось в: {time_start}\n" \
                  "Голосование закончится в: {time_end}\n" \
                  "Времени осталось: {time_left}\n"

owner_inline_keyboard = types.InlineKeyboardMarkup()
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Начать голосование", callback_data="vote_start"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Выбрать вопрос", callback_data="vote_choose"))

member_inline_keyboard = types.InlineKeyboardMarkup()
member_inline_keyboard.add(
    types.InlineKeyboardButton(text="Вариант А", callback_data="vote_a"),
    types.InlineKeyboardButton(text="Вариант Б", callback_data="vote_b")
)

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
bot = TeleBot(token=APP_TOKEN)

logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler("test.log", "w", "utf-8"))


# flask
# =================================================================================================================

@server.route("/vote")
def vote_result():
    result = "<h1>Результаты</h1>"

    return result, 200


@server.route(f"/{APP_TOKEN}", methods=["POST"])
def bot_webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


# telegram
# =================================================================================================================

@bot.message_handler(commands=["start"], chat_types=["private"])
def command_start(message):
    if message.from_user.id in [owner["telegram_id"] for owner in owner_list]:
        bot.send_message(
            chat_id=message.from_user.id,
            text=OWNER_MENU_TEXT.format(
                time_current=datetime.now(tz=timezone(timedelta(hours=5))).strftime("%H:%M:%S"),
                question_current=2,
                time_start=3,
                time_end=4,
                time_left=5
            ),
            reply_markup=owner_inline_keyboard
        )

    elif message.from_user.id in [member["telegram_id"] for member in member_list]:
        bot.send_message(
            chat_id=message.from_user.id,
            text="Вы уже зарегистрировались! Ожидайте начала."
        )

    else:
        pass


@bot.callback_query_handler(lambda call: True)
def handler_query(call):
    bot.edit_message_text(
        chat_id=call.message.from_user.id,
        message_id=call.message.message_id,
        text="Вы начали голосование",
        reply_markup=owner_inline_keyboard
    )

    for owner in owner_list:
        bot.send_message(
            chat_id=owner["telegram_id"],
            text="Голосование началось",
            reply_markup=member_inline_keyboard
        )


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL + APP_TOKEN)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
