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
                "<b>Голосование запущено:</b> {}\n\n" \
                "Выберите параметр для редактирования:"

member_text = "<b>[Голосование]</b>\n\n" \
              "<b>Вопрос:</b>\n{}\n\n" \
              "<b>Варианты ответа:</b>\nА) <i>{}</i>\nБ) <i>{}</i>\n\n"

member_text_answer1_underline = "<b>[Голосование]</b>\n\n" \
                                "<b>Вопрос:</b>\n{}\n\n" \
                                "<b>Варианты ответа:</b>\n<u>А) <i>{}</i></u>\nБ) <i>{}</i>\n\n"

member_text_answer2_underline = "<b>[Голосование]</b>\n\n" \
                                "<b>Вопрос:</b>\n{}\n\n" \
                                "<b>Варианты ответа:</b>\nА) <i>{}</i>\n<u>Б) <i>{}</i></u>\n\n"

owner_inline_keyboard = types.InlineKeyboardMarkup()
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Начать голосование", callback_data="owner_start"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Параметры голосования", callback_data="owner_settings"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Завершить голосование", callback_data="owner_end"))
owner_inline_keyboard.add(types.InlineKeyboardButton(text="Результаты голосования", url=app_url))

settings_inline_keyboard = types.InlineKeyboardMarkup()
settings_inline_keyboard.add(types.InlineKeyboardButton(text="Сменить вопрос", callback_data="settings_question"))
settings_inline_keyboard.add(
    types.InlineKeyboardButton(text="Сменить ответ А", callback_data="settings_answer1"),
    types.InlineKeyboardButton(text="Сменить ответ Б", callback_data="settings_answer2")
)
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


@server.route("/")
def app_result():
    is_active = mysql_execute(
        mysql_host, mysql_user, mysql_passwd, mysql_db,
        query="SELECT is_active FROM system"
    )[0]

    if is_active:
        question, answer1, answer2 = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM system"
        )[1:4]

        count_answer1 = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT COUNT(answer) FROM member WHERE answer = 1"
        )[0]
        count_answer2 = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT COUNT(answer) FROM member WHERE answer = 2"
        )[0]

    else:
        _id, question, answer1, answer2, count_answer1, count_answer2 = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM history ORDER BY id DESC LIMIT 1"
        )

    head = "<head>" \
           "<meta charset='utf-8'>" \
           "<title>Результаты голосования</title>" \
           "<style>" \
           "body {font-family: Roboto, sans-serif;}" \
           "h2 {color: #414a5f; margin-bottom: 0px; font-weight: 700; font-size: 40px; line-height: 2.5;}" \
           "h3 {color: #003347; margin-bottom: 0px; font-weight: 700; font-size: 32px; line-height: 2.5;}" \
           "span {font-size: 24px;}" \
           "ul {list-style: none; padding-left: 0; font-size: 16px;}" \
           "</style>" \
           "</head>"

    body = f"<body><div>" \
           f"<h2>Голосование {'началось' if is_active else 'завершено'}!</h2>" \
           f"<h3 align='left'>Вопрос:</h3>" \
           f"<span align='justify'>{question}</span>" \
           f"<h3 align='left'>Варианты ответа:</h3>" \
           f"<ul><li><div align='left'>А) {answer1} – <b>{count_answer1}</b></div></li>" \
           f"<li><div align='left'>Б) {answer2} – <b>{count_answer2}</b></div></li></ul>" \
           f"</div></body>"

    return "<html>" + head + body + "</html>", 200


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
        question, answer1, answer2, is_active = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT * FROM system"
        )[1:]

        if not is_active:
            bot.send_message(
                chat_id=message.from_user.id,
                text="Вы уже зарегистрированы. Ожидайте начала голосования"
            )

            return

        answer = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT answer FROM member WHERE telegram_id = {message.from_user.id}"
        )[0]

        if answer == 1:
            bot.send_message(
                chat_id=message.from_user.id,
                text=member_text_answer1_underline.format(question, answer1, answer2),
                parse_mode="HTML",
                reply_markup=member_inline_keyboard
            )
        elif answer == 2:
            bot.send_message(
                chat_id=message.from_user.id,
                text=member_text_answer2_underline.format(question, answer1, answer2),
                parse_mode="HTML",
                reply_markup=member_inline_keyboard
            )

        else:
            bot.send_message(
                chat_id=message.from_user.id,
                text=member_text.format(question, answer1, answer2),
                parse_mode="HTML",
                reply_markup=member_inline_keyboard
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
        bot.answer_callback_query(call.id)

        if is_active:
            return

        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="UPDATE system SET is_active = 1 WHERE id = 1"
        )
        is_active = 1

        telegram_id_list = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="SELECT telegram_id FROM member"
        )
        if telegram_id_list:
            for telegram_id in telegram_id_list:
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
        bot.answer_callback_query(call.id)

        if not is_active:
            return

        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="UPDATE system SET is_active = 0 WHERE id = 1"
        )
        is_active = 0

        telegram_id_list = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query="SELECT telegram_id FROM member"
        )
        if telegram_id_list:
            for telegram_id in telegram_id_list:
                bot.send_message(
                    chat_id=telegram_id,
                    text="Голосование завершено. Благодарим за участие."
                )

        count_answer1 = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT COUNT(answer) FROM member WHERE answer = 1"
        )[0]
        count_answer2 = mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"SELECT COUNT(answer) FROM member WHERE answer = 2"
        )[0]
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"INSERT INTO history (question, answer1, answer2, count_answer1, count_answer2) "
                  f"VALUES ('{question}', '{answer1}', '{answer2}', {count_answer1}, {count_answer2})"
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
            reply_markup=owner_inline_keyboard
        )


@bot.callback_query_handler(lambda call: call.data.startswith("settings_"))
def keyboard_settings(call):
    bot.answer_callback_query(call.id)

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


@bot.callback_query_handler(lambda call: call.data.startswith("member_"))
def keyboard_member(call):
    bot.answer_callback_query(call.id)

    question, answer1, answer2, is_active = mysql_execute(
        mysql_host, mysql_user, mysql_passwd, mysql_db,
        query=f"SELECT * FROM system"
    )[1:]

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

        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=member_text_answer1_underline.format(question, answer1, answer2),
            parse_mode="HTML",
            reply_markup=member_inline_keyboard
        )

    elif call.data == "member_answer2":
        mysql_execute(
            mysql_host, mysql_user, mysql_passwd, mysql_db,
            query=f"UPDATE member SET answer = 2 WHERE telegram_id = {call.from_user.id}"
        )

        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=member_text_answer2_underline.format(question, answer1, answer2),
            parse_mode="HTML",
            reply_markup=member_inline_keyboard
        )

    bot.send_message(
        chat_id=call.from_user.id,
        text="Ваш голос учтен. Ожидайте завершения голосования."
    )


def main():
    bot.remove_webhook()
    bot.set_webhook(url=app_url + app_token)
    server.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))


if __name__ == "__main__":
    main()
