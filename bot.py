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

owner_list = []
with pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DATABASE) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM `owner`")
        for fetch in cursor.fetchall():
            telegram_id, telegram_username, telegram_firstname, telegram_lastname = fetch[:4]
            owner_list.append({
                telegram_id: {
                    "telegram_username": telegram_username,
                    "telegram_firstname": telegram_firstname,
                    "telegram_lastname": telegram_lastname
                }
            })

member_list = []
with pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DATABASE) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM `member`")
        for fetch in cursor.fetchall():
            telegram_id, telegram_username, telegram_firstname, telegram_lastname = fetch[:4]
            owner_list.append({
                telegram_id: {
                    "telegram_username": telegram_username,
                    "telegram_firstname": telegram_firstname,
                    "telegram_lastname": telegram_lastname
                }
            })

server = Flask(__name__)
bot = TeleBot(token=APP_TOKEN)


@server.route(f"/{APP_TOKEN}", methods=["POST"])
def bot_webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


@bot.message_handler(commands=["start"], chat_types=["private"])
def command_start(message):
    print(type(message.from_user.id))
    if message.from_user.id in owner_list:
        print(1)

    elif message.from_user.id in member_list:
        print(2)

    else:
        print(3)


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL + APP_TOKEN)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
