# -*- coding: utf-8 -*-
import os
import logging
import time
import json
from configparser import ConfigParser

import flask
import telebot

from budget_bot import BudgetBot
from budget_bot import send_message_telegram
from encryption import get_dict_from_encrypt_data

# set settings
config = ConfigParser()
dir_path = os.path.dirname(os.path.abspath(__file__))
config.read(dir_path + '/config/app.ini')

PRIVATE_COMMANDS = [command.strip() for command in config.get('BUDGET_BOT', 'private_commands').split(',')]
SUPERUSER_COMMANDS = [command.strip() for command in config.get('BUDGET_BOT', 'superuser_commands').split(',')]
WEBHOOK_URL_BASE = 'https://%s:%s' % (config.get('FLASK', 'webhook_host'), config.get('FLASK', 'webhook_port'))
WEBHOOK_URL_PATH = '/%s/' % config.get('BUDGET_BOT', 'token')

app = flask.Flask(__name__, static_url_path='')
bot = BudgetBot()
bot.remove_webhook()  # Remove webhook, it fails sometimes the set if there is a previous webhook
time.sleep(1)
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)


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


@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route("/agreement")
def agreement():
    return flask.render_template('agreement.html')


@app.route("/help")
def help_():
    return flask.render_template('helping.html')


@app.route('/simple_commands/v1/<command>/<user_info>')
def simple_commands(command, user_info):
    data = get_dict_from_encrypt_data(user_info)
    if not data or not data.get('user_id'):
        send_message_telegram(f'Error decrypt string: {user_info}', bot.chat_id_error_notification)
        return 'Ошибка'

    user_id = data.get('user_id')
    answer = bot.simple_commands(command=command, user_id=user_id)
    return str(answer) if answer else 'Нет данных'


@app.route('/monobank_api/v1/<user_info>', methods=['POST'])
def mono_api(user_info):
    if flask.request.data:
        logging.error('Request: ', json.loads(flask.request.data))

    data = get_dict_from_encrypt_data(user_info)

    user_id = data.get('user_id')
    chat_id = data.get('chat_id')

    if flask.request.headers.get('content-type') == 'application/json':
        if flask.request.data:
            request_data = json.loads(flask.request.data)
            type_request = request_data.get('type')
            if type_request == 'webhook_test':
                return jsonify({'webhook_test': True})
            elif type_request == 'StatementItem':

                # TODO разобраться с ошибкой если приходит когда транзакция приходит не в гривне
                if user_id and chat_id and request_data['data']['statementItem']['currencyCode'] == 980:
                    merchant_id = request_data['data']['account']
                    data_mono = request_data['data']['statementItem']

                    data = {
                        'bank': 'Monobank',
                        'chat_id': chat_id,
                        'user_id': user_id,
                        'message_id': data_mono['time'],
                        'merchant_id': merchant_id,
                        'transaction_id': data_mono['id'],
                        'date_create': datetime.datetime.fromtimestamp(int(data_mono['time'])).strftime(
                            '%Y-%m-%d %H:%M:%S'),
                        'amount': abs(data_mono['amount']),
                        'commission': data_mono['commissionRate'],
                        'cashback': data_mono['cashbackAmount'],
                        'currency_code': data_mono['currencyCode'],
                        'description': data_mono['description'],
                        'card_balance': data_mono['balance'],
                        'type': 'monobank_api',
                        'status': 0,
                        'message_text': '',
                        'is_income': data_mono['amount'] >= 0

                    }
                    if bot.add_from_api(data_api=data) is False:
                        message_tex = 'Budget_bot Error,\nError: error add data from monobank api'
                        if data.get('user_id'):
                            message_tex += f'\nUser id: {user_id}'
                        if flask.request.data:
                            message_tex += f'\nData: {json.loads(flask.request.data)}'
                        send_message_telegram(message_tex, bot.chat_id_error_notification)

                return 'OK'

    return flask.abort(403)


@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        logging.error('add new message')
        bot.process_new_updates([update])
        logging.error('Add: %s' % json_string)
        return ''
    else:
        flask.abort(403)


@bot.message_handler(commands=['add'])
@access_check
def add(message):
    bot.add(message)


@bot.message_handler(commands=['report'])
@access_check
def report(message):
    bot.report(message)


@bot.message_handler(commands=['settings'])
@access_check
def settings(message):
    bot.settings(message)


@bot.message_handler(commands=['help'])
def help_(message):
    bot.help(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    bot.callback_inline(call)


@bot.message_handler(content_types=['text'])
def text(message):
    bot.text(message)


@bot.message_handler(commands=['start'])
@access_check
def start(message):
    bot.start(message)


@bot.message_handler(commands=['ping'])
@access_check
def ping(message):
    bot.ping(message)


@bot.message_handler(commands=['send_for_all'])
@access_check
def send_for_all(message):
    bot.send_for_all(message)


@bot.message_handler(commands=['command_token'])
@access_check
def get_command_token(message):
    bot.get_command_token(message)


def main():
    logging.error('Run Budget Bot')
    bot.polling()
