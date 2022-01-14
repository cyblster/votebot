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

admin_list = []
member_list = []

server = Flask(__name__)
bot = TeleBot(token=APP_TOKEN)


def mysql_query(query: str, commit: bool = False):
    with pymysql.connect(
            host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)

            if commit:
                connection.commit()

            return cursor.fetchall()


@server.route(f"/{APP_TOKEN}", methods=["POST"])
def bot_webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


@bot.message_handler(commands=["start"], chat_types=["private"])
def command_start(message):
    if message.from_user.id in admin_list:
        inline_keyboard = types.InlineKeyboardMarkup()
        inline_keyboard.add(
            types.InlineKeyboardButton(text="Начать голосование", callback_data="button_start"),
        )
        inline_keyboard.add(
            types.InlineKeyboardButton(text="Выбрать вопрос", callback_data="button_choose"),
        )

        bot.send_message(
            chat_id=message.from_user.id,
            text="Меню",
            reply_markup=inline_keyboard
        )

    else:
        if message.from_user.id not in member_list:
            telegram_id = message.from_user.id
            telegram_username = message.from_user.username
            telegram_firstname = message.from_user.firstname
            telegram_lastname = message.from_user.lastname

            if not telegram_username:
                telegram_username = "NULL"
            if not telegram_firstname:
                telegram_firstname = "NULL"
            if not telegram_lastname:
                telegram_lastname = "NULL"

            mysql_query(
                f"INSERT INTO users (telegram_id, telegram_username, telegram_firstname, telegram_lastname) "
                f"VALUES ({telegram_id}, {telegram_username}, {telegram_firstname}, {telegram_lastname})",

                commit=True
            )

            member_list.append({
                telegram_id: {
                    "telegram_username": telegram_username,
                    "telegram_firstname": telegram_firstname,
                    "telegram_lastname": telegram_lastname
                }
            })


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL + APP_TOKEN)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

    for fetch in mysql_query("SELECT * FROM users"):
        member_list.append({
            fetch[0]: {  # Telegram ID
                "telegram_username": fetch[1],
                "telegram_firstname": fetch[2],
                "telegram_lastname": fetch[3]
            }
        })
