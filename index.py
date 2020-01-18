# -*- coding: utf-8 -*-
import os
import logging
import time

from configparser import ConfigParser

from budget_bot import BudgetBot
from sheets_api import SheetsApi
import telebot

config = ConfigParser()
dir_path = os.path.dirname(os.path.abspath(__file__))
config.read(dir_path + '/config/app.ini')

sheet_api = SheetsApi()
bot = BudgetBot()
bot.remove_webhook()
time.sleep(1)

PRIVATE_COMMANDS = [command.strip() for command in config.get('BUDGET_BOT', 'private_commands').split(',')]
SUPERUSER_COMMANDS = [command.strip() for command in config.get('BUDGET_BOT', 'superuser_commands').split(',')]


def access_check(func):
    def wrapper(*args, **kwargs):
        if args and isinstance(args[0], telebot.types.Message):
            message = args[0]

            if message.from_user.is_bot:
                return
            if not bot.db.can_work_in_group(message.from_user.id) and message.chat.id != message.from_user.id:
                bot.send_message(chat_id=message.chat.id,
                                 text='Работа в группе отключена. Зайдите в настройки бота и откройте доступ.')
                return

            command = message.text.replace('/', '').split(' ')[0]
            if command in PRIVATE_COMMANDS and message.chat.id != message.from_user.id:
                bot.send_message(chat_id=message.chat.id,
                                 text='Эту команду можно использовать только в приватных сообщениях.')
                return

            if command in SUPERUSER_COMMANDS and message.from_user.id not in bot.superusers:
                return

        return func(*args, **kwargs)

    return wrapper


@bot.message_handler(commands=['add'])
def add(message):
    bot.add(message)


@bot.message_handler(commands=['settings'])
def settings(message):
    bot.settings(message)


@bot.message_handler(commands=['report'])
def report(message):
    bot.report(message)


@bot.message_handler(commands=['help'])
def help_(message):
    bot.help(message)


@bot.message_handler(commands=['start'])
def start(message):
    bot.start(message)


@bot.message_handler(commands=['ping'])
@access_check
def ping(message):
    logging.error('ping OK')
    bot.reply_to(message, 'Привет 👋\n Я работаю 😎')


@bot.message_handler(commands=['send_for_all'])
@access_check
def send_for_all(message):
    bot.send_for_all(message)


@bot.message_handler(commands=['command_token'])
def get_command_token(message):
    bot.get_command_token(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    bot.callback_inline(call)


@bot.message_handler(content_types=['text'])
def text(message):
    bot.text(message)


def main():
    logging.error('Run Budget Bot')
    bot.polling()


if __name__ == '__main__':
    main()
