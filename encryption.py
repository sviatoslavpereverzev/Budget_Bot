# -*- coding: utf-8 -*-
import os
import logging

from cryptography.fernet import Fernet


def encrypt(data):
    with open(os.path.dirname(os.path.realpath(__file__)) + '/private/key_for_name.txt') as file:
        key = file.read().encode('utf-8')
    cipher = Fernet(key)
    return cipher.encrypt(str(data).encode('utf-8')).decode('utf-8')


def decrypt(data):
    with open(os.path.dirname(os.path.realpath(__file__)) + '/private/key_for_name.txt') as file:
        key = file.read().encode('utf-8')
    cipher = Fernet(key)
    return cipher.decrypt(data.encode('utf-8')).decode('utf-8')


def get_dict_from_encrypt_data(encrypt_data):
    try:
        return {k: v for k, v in (val.split(':') for val in decrypt(encrypt_data).split(';'))}
    except Exception as e:
        message_text = f'Error decrypt string: {encrypt_data}. Error: {e}'
        logging.error(message_text)

