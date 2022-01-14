import os

from flask import Flask, request
from telebot import TeleBot, types


APP_URL = os.environ.get("app_url")
APP_TOKEN = os.environ.get("app_token")

WHITE_LIST = (418064835, )  # Telegram ID, кому доступны команды

server = Flask(__name__)
bot = TeleBot(token=APP_TOKEN)


@server.route(f"/{APP_TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


@bot.message_handler(commands=["start"], chat_types=["private"])
def command_start(message):
    if message.from_user.id in WHITE_LIST:
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
        pass


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL + APP_TOKEN)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
