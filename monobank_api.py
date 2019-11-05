# -*- coding: utf-8 -*-
import json
import logging
import requests


def get_user_info(user_token):
    header = {'X-Token': user_token, 'accept': 'application/json', 'Content-Type': 'application/json', }
    response = requests.get('https://api.monobank.ua//personal/client-info', headers=header)
    if not response:
        if response.status_code == 403 and 'errorDescription' in response.text:
            return {'error': 'Token Error'}

        logging.error('Error get card balance for monobank. Last token symbol: %s' % user_token[-10:])
        if response.content:
            logging.error(response.content.decode('utf-8'))
        return

    return json.loads(response.content, encoding='utf-8')


def get_cost_statement(user_token, time_from, time_to=None, account=0):
    header = {'X-Token': user_token, 'accept': 'application/json', 'Content-Type': 'application/json', }
    url = 'https://api.monobank.ua//personal/statement/%s/%s/' % (account, time_from)
    if time_to:
        url += str(time_to)
    response = requests.get(url, headers=header)
    if not response:
        logging.error('Error get card balance for monobank. Last token symbol: %s' % user_token[-10:])
        return

    return json.loads(response.content, encoding='utf-8')


def set_webhook(user_token, url):
    header = {'X-Token': user_token, 'accept': 'application/json', 'Content-Type': 'application/json', }
    data = {'webHookUrl': url}
    try:
        response = requests.post('https://api.monobank.ua/personal/webhook', data=json.dumps(data), headers=header)
    except:
        logging.error('Error set webhook for monobank cards. Last token symbol: %s' % user_token[-10:])
        return

    return json.loads(response.content, encoding='utf-8')


def get_webhook(user_token):
    user_info = get_user_info(user_token)
    if user_info:
        if user_info.get('webHookUrl'):
            return user_info.get('webHookUrl')
        elif user_info.get('error'):
            return user_info.get('error')


def get_currency():
    response = requests.get('https://api.monobank.ua/bank/currency')
    return json.loads(response.content, encoding='utf-8')
