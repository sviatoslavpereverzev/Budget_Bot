# -*- coding: utf-8 -*-
import logging
from threading import Thread

from budget_bot import BudgetBot
from sheets_api import SheetsApi

# написать файл README
# написать обработку исключений и логонизацию так, чтоб бот перезапускался

sheet_api = SheetsApi()
bot = BudgetBot()
bot.remove_webhook()
import time

time.sleep(1)
import telebot


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
    # run_func = [sheet_api.main, main]
    # run_processes = []
    # for func in run_func:
    #     p = Thread(target=func)
    #     p.start()
    #     run_processes.append(p)
    #
    # for p in run_processes:
    #     p.join()
