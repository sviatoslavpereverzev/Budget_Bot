# -*- coding: utf-8 -*-
from budget_bot import BudgetBot

# дописать главную функцию с запуском парралельных процессов
# дописать start и help
# дописать комментарии если нужны
# удалить лишнее
# написать файл README

bot = BudgetBot()


@bot.message_handler(commands=['add'])
def add(message):
    print('add')
    bot.add(message)


@bot.message_handler(commands=['settings'])
def settings(message):
    print('settings')
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
    print('callback_inline')
    bot.callback_inline(call)


@bot.message_handler(content_types=['text'])
def text(message):
    print('text')
    bot.text(message)


def main():
    bot.polling()


if __name__ == '__main__':
    main()
