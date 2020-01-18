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


@bot.message_handler(commands=['add'])
def add(message):
    bot.add(message)


@bot.message_handler(commands=['settings'])
def settings(message):
    bot.settings(message)


@bot.message_handler(commands=['report'])
def report(message):
    bot.report(message)


@bot.message_handler(commands=['start'])
def start(message):
    bot.start(message)


@bot.message_handler(commands=['help'])
def help_(message):
    bot.help(message)


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
