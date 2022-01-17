import logging
from os import environ

from flask import Flask, request
from telebot import TeleBot, types, logger
from pymysql import connect

app_url = environ.get("app_url")
app_token = environ.get("app_token")

mysql_host = environ.get("mysql_host")
mysql_user = environ.get("mysql_user")
mysql_passwd = environ.get("mysql_password")
mysql_db = environ.get("mysql_database")

owner_menu_text = "<b>[Меню]</b>\n\n" \
                  "<b>Вопрос:</b>\n{}\n\n" \
                  "<b>Варианты ответа:</b>\nА) <i>{}</i>\nБ) <i>{}</i>\n\n" \
                  "<b>Голосование запущено:</b> {}"

settings_text = "<b>[Параметры голосования]</b>\n\n" \
                "<b>Вопрос:</b>\n{}\n\n" \
                "<b>Варианты ответа:</b>\nА) <i>{}</i>\nБ) <i>{}</i>\n\n" \
                "<b>Голосование активно:</b> {}\n\n" \
                "Выберите параметр для редактирования:"

member_text = "<b>[Голосование]</b>\n\n" \
              "<b>Вопрос:</b>\n{}\n\n" \
              "<b>Варианты ответа:</b>\nА) <i>{}</i>\nБ) <i>{}</i>\n\n"

owner_inline_keyboard = types.InlineKeyboardMarkup()
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Начать голосование", callback_data="owner_start"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Параметры голосования", callback_data="owner_settings"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Закончить голосование", callback_data="owner_end"))

settings_inline_keyboard = types.InlineKeyboardMarkup()
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Сменить вопрос", callback_data="settings_question"))
settings_inline_keyboard.add(
    types.InlineKeyboardButton(text="Сменить ответ А", callback_data="settings_answer1"),
    types.InlineKeyboardButton(text="Сменить ответ Б", callback_data="settings_answer2")
)
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Сбросить результаты", callback_data="settings_clear"))
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data="settings_exit"))

member_inline_keyboard = types.InlineKeyboardMarkup()
member_inline_keyboard.add(
    types.InlineKeyboardButton(text="Вариант А", callback_data="member_answer1"),
    types.InlineKeyboardButton(text="Вариант Б", callback_data="member_answer2")
)
member_inline_keyboard.add(
    types.InlineKeyboardButton(text="Результаты голосования", url=app_url)
)

setting_question_is_active = False
setting_answer1_is_active = False
setting_answer2_is_active = False

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


@server.route(f"/{app_token}", methods=["POST"])
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
        _id, question, answer1, answer2, is_active = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM system"
        )

        bot.send_message(
            chat_id=message.from_user.id,
            text=owner_menu_text.format(question, answer1, answer2, "Да" if is_active else "Нет"),
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
        is_active = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="SELECT is_active FROM system"
        )[0]

        if is_active:
            bot.send_message(
                chat_id=message.from_user.id,
                text="Голосование уже началось. Ожидайте завершения голосования."
            )

            return

        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"INSERT INTO member (telegram_id) VALUES ({message.from_user.id})"
        )

        bot.send_message(
            chat_id=message.from_user.id,
            text="Вы успешно зарегистрировались. Ожидайте начала голосования."
        )


@bot.message_handler(content_types=["text"], chat_types=["private"])
def message_any(message):
    if not mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM owner WHERE telegram_id = {message.from_user.id}"
    ):
        return

    global setting_question_is_active
    global setting_answer1_is_active
    global setting_answer2_is_active

    if setting_question_is_active:
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"UPDATE system SET question = '{message.text}' WHERE id = 1"
        )
    
    elif setting_answer1_is_active:
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"UPDATE system SET answer1 = '{message.text}' WHERE id = 1"
        )
    
    elif setting_answer2_is_active:
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"UPDATE system SET answer2 = '{message.text}' WHERE id = 1"
        )

    if setting_question_is_active or setting_answer1_is_active or setting_answer2_is_active:
        question, answer1, answer2, is_active = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM system"
        )[1:]

        bot.send_message(
            chat_id=message.from_user.id,
            text=settings_text.format(question, answer1, answer2, "Да" if is_active else "Нет"),
            parse_mode="HTML",
            reply_markup=settings_inline_keyboard
        )

    setting_question_is_active = False
    setting_answer1_is_active = False
    setting_answer2_is_active = False


@bot.callback_query_handler(lambda call: call.data.startswith("owner_"))
def keyboard_owner(call):
    question, answer1, answer2, is_active = mysql_execute(
        mysql_host, mysql_user, mysql_passwd, mysql_db,
        query=f"SELECT * FROM system"
    )[1:]

    if call.data == "owner_start":
        if is_active:
            return

        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="UPDATE system SET is_active = 1 WHERE id = 1"
        )

        for telegram_id in mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="SELECT telegram_id FROM member"
        ):
            bot.send_message(
                chat_id=telegram_id,
                text=member_text.format(question, answer1, answer2),
                parse_mode="HTML",
                reply_markup=member_inline_keyboard
            )

        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=owner_menu_text.format(question, answer1, answer2, "Да" if is_active else "Нет"),
            parse_mode="HTML",
            reply_markup=owner_inline_keyboard
        )

    elif call.data == "owner_settings":
        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=settings_text.format(question, answer1, answer2, "Да" if is_active else "Нет"),
            parse_mode="HTML",
            reply_markup=settings_inline_keyboard
        )

    elif call.data == "owner_end":
        if not is_active:
            return

        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="UPDATE system SET is_active = 0 WHERE id = 1"
        )

        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="TRUNCATE TABLE member"
        )

        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=owner_menu_text.format(question, answer1, answer2, "Да" if is_active else "Нет"),
            parse_mode="HTML",
            reply_markup=settings_inline_keyboard
        )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(lambda call: call.data.startswith("settings_"))
def keyboard_settings(call):
    global setting_question_is_active
    global setting_answer1_is_active
    global setting_answer2_is_active
    
    question, answer1, answer2, is_active = mysql_execute(
        mysql_host, mysql_user, mysql_passwd, mysql_db,
        query=f"SELECT * FROM system"
    )[1:]

    if call.data == "settings_question":
        setting_question_is_active = True
        setting_answer1_is_active = False
        setting_answer2_is_active = False
        
        bot.send_message(
            chat_id=call.from_user.id,
            text="Напишите текст для вопроса:"
        )

    elif call.data == "settings_answer1":
        setting_question_is_active = False
        setting_answer1_is_active = True
        setting_answer2_is_active = False

        bot.send_message(
            chat_id=call.from_user.id,
            text="Напишите текст для варианта ответа А:"
        )

    elif call.data == "settings_answer2":
        setting_question_is_active = False
        setting_answer1_is_active = False
        setting_answer2_is_active = True

        bot.send_message(
            chat_id=call.from_user.id,
            text="Напишите текст для варианта ответа Б:"
        )

    elif call.data == "settings_exit":
        setting_question_is_active = False
        setting_answer1_is_active = False
        setting_answer2_is_active = False
        
        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=owner_menu_text.format(question, answer1, answer2, "Да" if is_active else "Нет"),
            parse_mode="HTML",
            reply_markup=owner_inline_keyboard
        )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(lambda call: call.data.startswith("member_"))
def keyboard_member(call):
    is_active = mysql_execute(
        mysql_host, mysql_user, mysql_passwd, mysql_db,
        query="SELECT is_active FROM system"
    )[0]

    answer = mysql_execute(
        mysql_host, mysql_user, mysql_passwd, mysql_db,
        query=f"SELECT answer FROM member WHERE telegram_id = {call.from_user.id}"
    )[0]

    if not is_active:
        bot.send_message(
            chat_id=call.from_user.id,
            text="Голосование еще не началось. Ожидайте начала голосования."
        )

        return

    if answer:
        bot.send_message(
            chat_id=call.from_user.id,
            text="Вы уже проголосовали. Ожидайте завершения голосования."
        )

        return

    if call.data == "member_answer1":
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"UPDATE member SET answer = 1 WHERE telegram_id = {call.from_user.id}"
        )

    elif call.data == "member_answer2":
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"UPDATE member SET answer = 2 WHERE telegram_id = {call.from_user.id}"
        )

    bot.send_message(
        chat_id=call.from_user.id,
        text="Ваш голос учтен. Ожидайте завершения голосования."
    )

    bot.answer_callback_query(call.id)


def main():
    bot.remove_webhook()
    bot.set_webhook(url=app_url + app_token)
    server.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))


if __name__ == "__main__":
    main()
