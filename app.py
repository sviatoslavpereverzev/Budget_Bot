# -*- coding: utf-8 -*-
import os
import logging
import time
import datetime
import json
import flask
import telebot
from configparser import ConfigParser
from flask import jsonify

from encryption import decrypt
from budget_bot import BudgetBot, send_message_telegram

config = ConfigParser()
dir_path = os.path.dirname(os.path.abspath(__file__))
config.read(dir_path + '/config/app.ini')

API_TOKEN = config.get('BUDGET_BOT', 'token')
WEBHOOK_HOST = config.get('FLASK', 'webhook_host')
WEBHOOK_PORT = config.get('FLASK', 'webhook_port')
WEBHOOK_LISTEN = config.get('FLASK', 'webhook_listen')
WEBHOOK_SSL_CERT = dir_path + '/private/fullchain.pem'
WEBHOOK_SSL_PRIV = dir_path + '/private/privkey.pem'
WEBHOOK_URL_BASE = 'https://%s:%s' % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = '/%s/' % API_TOKEN

bot = BudgetBot()
app = flask.Flask(__name__)

# Remove webhook, it fails sometimes the set if there is a previous webhook
bot.remove_webhook()
time.sleep(1)

# Set webhook
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)

# Настройки логирования
os.makedirs(dir_path + '/logs/', exist_ok=True)
logfile = dir_path + '/logs/main.log'
logger = logging.getLogger()
formatter = logging.Formatter(u'%(filename) s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]: \n%(message)s')


@app.route('/')
def hello_world():
    return 'Budget App'


@app.route('/offer')
def offer():
    return 'УУУуупппссс, я еще это не дописал'


@app.route('/notification', methods=['POST', 'GET'])
def notification():
    request_data = json.loads(flask.request.data)
    chat_id = request_data.get('chat_id')
    message_text = request_data.get('message_text')
    if chat_id and message_text:
        send_message_telegram(str(message_text), str(chat_id))
    return 'OK'


@app.route('/simple_commands/v1/<command>/<user_info>')
def simple_commands(command, user_info):
    data = get_dict_from_encrypt_data(user_info)
    user_id = data.get('user_id')
    if user_id:
        answer = bot.simple_commands(command=command, user_id=user_id)
        return str(answer) if answer else 'Нет данных'
    else:
        return 'Ошибка токена'


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
                if user_id and chat_id:
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


@bot.message_handler(commands=['ping'])
def send_welcome(message):
    logging.error('ping OK')
    bot.reply_to(message, 'Привет 👋\n Я работаю 😎')


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


def get_dict_from_encrypt_data(encrypt_data):
    data = {}

    try:
        decrypt_data = decrypt(encrypt_data)
        data = {k: v for k, v in (val.split(':') for val in decrypt_data.split(';'))}

    except:
        message_text = f'Error decrypt string: {encrypt_data}'
        send_message_telegram(message_text, bot.chat_id_error_notification)

    return data


if __name__ == '__main__':
    dir_path = os.path.dirname(os.path.realpath(__file__))
    logging.basicConfig(level=logging.DEBUG,
                        format=u'%(filename) s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]: \n%(message)s',
                        filename='%s/logs/budget.log' % dir_path, )
    # Start flask server
    app.run(host='0.0.0.0',
            port=8080, )  # ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV), )
