# -*- coding: utf-8 -*-
import logging

import telebot


def delete_message(*args, **kwargs):
    def delete(self, chat_id_, message_id_):
        try:
            telebot.TeleBot.delete_message(self, chat_id_, message_id_)
        except Exception as e:
            logging.error('Error delete message. Error: %s' % e)

    if kwargs and kwargs.get('chat_id') and kwargs.get('message_id'):
        self = args[0]
        delete(self, kwargs.get('chat_id'), kwargs.get('message_id'))
        return

    func = args[0]

    def wrap(self, arg, *args, **kwargs):
        if isinstance(arg, telebot.types.CallbackQuery):
            call = arg
            delete(self, call.message.chat.id, call.message.message_id)
            return func(self, call, *args, **kwargs)

        elif isinstance(arg, telebot.types.Message):
            message = arg
            delete(self, message.chat.id, message.message_id)
            return func(self, message, *args, **kwargs)

    return wrap
