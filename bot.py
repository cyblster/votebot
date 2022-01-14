import os
import telebot

from telebot import types


WHITE_LIST = (418064835, )  # Telegram ID, кому доступны команды

bot = telebot.TeleBot(token=os.environ.get("bot_token"))


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



bot.polling()
