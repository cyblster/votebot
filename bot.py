import logging
from os import environ

import pymysql.cursors
from flask import Flask, request
from telebot import TeleBot, types, logger
from pymysql import connect


app_url = environ.get("app_url")
app_token = environ.get("app_token")

mysql_host = environ.get("mysql_host")
mysql_user = environ.get("mysql_user")
mysql_passwd = environ.get("mysql_password")
mysql_db = environ.get("mysql_database")

owner_menu = "<b>[Меню]</b>\n\n" \
             "Вопрос: {question}\n" \
             "Ответ А: {answer1}\n" \
             "Ответ Б: {answer2}\n\n" \
             "Активно: {is_active}"

owner_inline_keyboard = types.InlineKeyboardMarkup()
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Начать голосование", callback_data="owner_start"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Параметры голосования", callback_data="owner_settings"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Закончить голосвание", callback_data="owner_end"))

settings_inline_keyboard = types.InlineKeyboardMarkup()
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Сменить вопрос", callback_data="settings_question"))
settings_inline_keyboard.add(
    types.InlineKeyboardButton(text="Сменить ответ А", callback_data="settings_answer1"),
    types.InlineKeyboardButton(text="Сменить ответ Б", callback_data="settings_answer2")
)
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Сбросить результаты", callback_data="settings_question"))

member_inline_keyboard = types.InlineKeyboardMarkup()
owner_inline_keyboard.add(
    owner_inline_keyboard.add(types.InlineKeyboardButton(text="Вариант А", callback_data="member_answer1")),
    owner_inline_keyboard.add(types.InlineKeyboardButton(text="Вариант Б", callback_data="member_answer2"))
)

setting_question_is_active = False
setting_answer_a_is_active = False
setting_answer_b_is_active = False

server = Flask(__name__)
bot = TeleBot(app_token)

logger.setLevel(logging.DEBUG)


def mysql_execute(host: str, user: str, passwd: str, db: str, query: str, autocommit=True) -> tuple:
    with connect(host=host, user=user, passwd=passwd, db=db, autocommit=autocommit) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query=query)

            return cursor.fetchone()


# Website ===================================================================================================


@server.route("/result")
def app_result():
    pass


# Telegram ===================================================================================================


@server.route(f"/{app_token}")
def app_webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "", 200


@bot.message_handler(commands=["start"], chat_types=["private"])
def command_start(message):
    if mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM owner WHERE telegram_id = {message.from_user.id}"
    ):
        question, answer1, answer2, is_active = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM system"
        )[1:5]

        bot.send_message(
            chat_id=message.from_user.id,
            text=owner_menu.format(question, answer1, answer2, is_active),
            parse_mode="HTML",
            reply_markup=owner_inline_keyboard
        )

    elif mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM member WHERE telegram_id = {message.from_user.id}"
    ):
        bot.send_message(
            chat_id=message.from_user.id,
            text="Вы уже зарегистрированы. Ожидайте начала голосования."
        )

    else:
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"INSERT INTO member (telegram_id) VALUES ({message.from_user.id})"
        )

        bot.send_message(
            chat_id=message.from_user.id,
            text="Вы успешно зарегистрировались. Ожидайте начала голосования."
        )


def main():
    bot.remove_webhook()
    bot.set_webhook(url=app_url + app_token)
    server.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))


if __name__ == "__main__":
    main()
