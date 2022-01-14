import os
import pymysql

from flask import Flask, request
from telebot import TeleBot, types


APP_URL = os.environ.get("app_url")
APP_TOKEN = os.environ.get("app_token")

MYSQL_HOST = os.environ.get("mysql_host")
MYSQL_USER = os.environ.get("mysql_user")
MYSQL_PASSWORD = os.environ.get("mysql_password")
MYSQL_DATABASE = os.environ.get("mysql_database")

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
            text="Тест меню",
            reply_markup=owner_inline_keyboard
        )

    elif message.from_user.id in [member["telegram_id"] for member in member_list]:
        print(2)

    else:
        print(3)


@bot.callback_query_handler(lambda call: call.data == "vote_start")
def handler_query(call):
    for owner in owner_list:
        bot.edit_message_text(
            chat_id=call.message.from_user.id,
            text="Вы начали голосование",
            reply_markup=owner_inline_keyboard
        )

        bot.send_message(
            chat_id=owner["telegram_id"],
            text="Голосование началось",
            reply_markup=member_inline_keyboard
        )


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL + APP_TOKEN)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
