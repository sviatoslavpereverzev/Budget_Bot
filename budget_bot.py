# -*- coding: utf-8 -*-
import os
import re
import logging
import requests
import json
import calendar
from datetime import datetime
from configparser import ConfigParser

import telebot
from telebot import types

from database import DB


# дописать help_data


class BudgetBot(telebot.TeleBot):
    def __init__(self):

        self.config = ConfigParser()
        self.config.read(os.path.dirname(os.path.abspath(__file__)) + '/app.ini')
        token = self.config.get('BUDGET_BOT', 'token')
        super().__init__(token)

        # database object
        self.db = None

        # maximum number of categories
        self.max_len_category = None
        # maximum number of subcategories
        self.max_len_subcategory = None

        # email bot to which to open access to the table
        self.email_budget_bot = None

        self.set_settings()

    def set_settings(self):
        self.db = DB()
        self.max_len_category = self.config.getint('BUDGET_BOT', 'max_len_category')
        self.max_len_subcategory = self.config.getint('BUDGET_BOT', 'max_len_subcategory')
        self.email_budget_bot = self.config.get('SHEETS_API', 'email_budget_bot')

    def keyboard(self, message, message_text, buttons, callback_key, previous_data, qt_key=3):
        """
        Keyboard for all methods

        Args:
            message (telebot.types.Message): Telebot object
            message_text (str): Text above the keyboard
            buttons (dict): Dictionary of buttons, where the key is the button identifier
            and the value is the name of the button
            callback_key (str): Key for keyback button
            previous_data (json): The date that came and is completed by the callback
            qt_key (int): Number of buttons in a row

        """

        callback = json.loads(previous_data, encoding='utf-8')
        list_keys = []
        keyboard = types.InlineKeyboardMarkup(row_width=qt_key)
        for button_id, button_name in buttons.items():
            callback[callback_key] = button_id
            callback_data_ = json.dumps(callback)
            list_keys.append(types.InlineKeyboardButton(button_name, callback_data=callback_data_))
        keyboard.add(*list_keys)
        self.send_message(message.chat.id, message_text, reply_markup=keyboard)

    def add(self, message):
        """Select income and expense categories"""

        try:
            self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass
        data = json.dumps({'f': 'amount'})
        categories = self.db.get_category(message.from_user.id)
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        self.keyboard(message, 'Выбери категорию:', buttons_name, callback_key='cat', previous_data=data)

    def settings(self, message):
        """Select Settings categories"""

        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'set_stng'})
        buttons_name = {1: 'Добавить', 2: 'Удалить', 3: 'Получить ссылку на Google таблицу',
                        4: 'Изменить ссылку на Google таблицу', 5: 'Отмена'}
        self.keyboard(message, 'Выбери настройки:', buttons_name, callback_key='cat', previous_data=data, qt_key=1, )

    def report(self, message):
        """Select report categories"""

        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'get_rp'})
        buttons_name = {1: 'День', 2: 'Неделя', 3: 'Месяц', 4: 'Определенный месяц'}
        self.keyboard(message, 'Отчет за:', buttons_name, callback_key='cat', previous_data=data, qt_key=1, )

    def start(self, message):
        """Adding a user to the database and welcome with user"""

        user_name = message.from_user.first_name
        user_name = '' if not user_name or user_name == 'None' else f', {user_name} '
        if not self.db.is_user(message.from_user.id):
            if self.db.add_user(message):
                message_text = f'Привет{user_name}👋\nBudget Bot поможет тебе контролировать твой бюджет 💸\n' + \
                               'Все доходы и расходы будут записываться в твою персональную Google Таблицу 😎\n' \
                               'Ты можешь строить любые графики, таблицы или делать расчеты благодаря данным, ' \
                               'которые будут в неё автоматически добавляться.\n' \
                               'Для того чтоб получить больше инфорвации используй команду \help.\n\n' \
                               'И на последок цитата Дэйва Рэмси:\n' \
                               '«Или ты будешь управлять своими деньгами, или их отсутствие будет управлять тобой.»'
                self.send_message(chat_id=message.chat.id, text=message_text)
        else:
            message_text = f'И снова привет{user_name}👋\nЕсли тебе нужна помощь используй команду \help.'
            self.send_message(chat_id=message.chat.id, text=message_text)

    def help(self, message):
        """Select categories for help the user"""

        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'help'})
        buttons_name = {1: 'Для чего нужен Budget Bot?',
                        2: 'Что он может?',
                        3: 'Как изменить Google Таблицу на другую?',
                        4: 'Как добавить затраты или доходы?',
                        5: 'Что за отчет?',
                        6: 'Как добавить/удалить категорию/подкатегорию?',
                        7: 'Получить данные для тех поддержки',
                        8: 'Отмена', }
        self.keyboard(message, 'Выбери настройки:', buttons_name, callback_key='id', previous_data=data, qt_key=1, )

    def help_data(self, call):
        """Sending help to the user"""

        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        all_messages = {1: 'Ok'}
        messages_id = int(callback_data.get('id'))
        message_text = all_messages.get(messages_id)
        if message_text:
            self.send_message(chat_id=call.message.chat.id, text=message_text)

    def get_amount(self, call):
        """Function to add income and expenses"""

        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        subcategories_dict = categories.get(callback_data.get('cat', ), {}).get('subcategories', {})

        if subcategories_dict and 'sub' not in callback_data:
            self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            subcategories_dict.items()}
            self.keyboard(call.message, 'Выберите подкатегорию:', buttons_name, callback_key='sub',
                          previous_data=call.data)
        else:
            category_name = categories.get(callback_data.get('cat'), {}).get('name')
            subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')
            if subcategories_dict:
                subcategory_name = f' Подкатегория: {subcategory_name}.'
            else:
                subcategory_name = ''
            text_message = f'Категория: {category_name}.{subcategory_name} Сумма: '
            self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            if category_name is None:
                self.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')
            else:
                self.send_message(chat_id=call.message.chat.id, text=text_message,
                                  reply_markup=types.ForceReply())

    def set_settings_bot(self, call):
        """Setting user preferences"""

        self.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        func_id = callback_data.get('cat')
        if func_id == 1:
            buttons_name = {11: 'Категорию', 12: 'Подкатегорию', }
            self.keyboard(call.message, 'Добавить:', buttons_name, callback_key='cat', previous_data=call.data, )
        elif func_id == 2:
            buttons_name = {21: 'Категорию', 22: 'Подкатегорию', }
            self.keyboard(call.message, 'Удалить:', buttons_name, callback_key='cat', previous_data=call.data, )
        elif func_id == 3:
            sheets_id = self.db.get_google_sheets_id(call.from_user.id)
            if sheets_id is None:
                self.send_message(chat_id=call.message.chat.id, text='Ссылка на Google таблицу не установлена')
            else:
                self.send_message(chat_id=call.message.chat.id, text='Ваша ссылка на Google таблицу:\n'
                                                                     'https://docs.google.com/spreadsheets/d/' + sheets_id)
        elif func_id == 4:
            if callback_data.get('yes'):
                self.send_message(chat_id=call.message.chat.id, text='Вставьте ссылку на вашу Google таблицу:',
                                  reply_markup=types.ForceReply())
            elif callback_data.get('yes') is None:
                buttons_name = {1: 'Да', 0: 'Нет', }
                message_text = f'Для того чтоб Budget Bot мог добавлять новые записи в Google таблицу, вам необходимо' \
                               f' открыть доступ на редактирование вашей таблицы для пользователя ' \
                               f'{self.email_budget_bot}'
                self.keyboard(call.message, message_text, buttons_name, callback_key='yes', previous_data=call.data, )
            elif not callback_data.get('yes'):
                message_text = 'Для того чтоб получить больше информации о том, как изменить Google таблицу ' \
                               'и окрытть доступ введите команду \help и перейдите в ' \
                               '"Как изменить Google Таблицу на другую?".'
                self.send_message(chat_id=call.message.chat.id, text=message_text)
        elif func_id == 11:
            buttons_name = {31: 'Доходы', 32: 'Расходы', }
            self.keyboard(call.message, 'Выберите тип категории:', buttons_name, callback_key='cat',
                          previous_data=call.data, )
        elif func_id == 12:
            categories = self.db.get_category(call.from_user.id)

            data = json.dumps({'f': 'add_s'})
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            categories.items()}
            self.keyboard(call.message, 'Выберите категорию:', buttons_name, callback_key='cat',
                          previous_data=data)
        elif func_id == 21:
            categories = self.db.get_category(call.from_user.id)

            data = json.dumps({'f': 'del', 'af': 1, 'a': 1})
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            categories.items()}
            self.keyboard(call.message, 'Удалить категорию:', buttons_name, callback_key='cat',
                          previous_data=data)
        elif func_id == 22:
            categories = self.db.get_category(call.from_user.id)
            data = json.dumps({'f': 'dels'})
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            categories.items()}
            self.keyboard(call.message, 'Выберите категорию:', buttons_name, callback_key='cat',
                          previous_data=data)
        elif func_id == 31 or func_id == 32:
            if self.db.can_add_category(call.from_user.id):
                self.send_message(chat_id=call.message.chat.id,
                                  text='Введите новое имя категории {}:'.format(
                                      'доходов' if func_id == 31 else 'расходов'),
                                  reply_markup=types.ForceReply())
            else:
                message_text = f'Нельзя добавлять больше {str(self.max_len_category)} категорий!'
                self.send_message(chat_id=call.message.chat.id, text=message_text)

    def prepare_report(self, call, report_for=None, exact_month=None):
        """
        Generate a report for a specific period

        Args:
            call (telebot.types.CallbackQuer): Telebot object
            report_for (int): Select report type
            exact_month (str): The row of the month number and the last digit of the year divided by '_'

        """

        c = calendar.Calendar()
        month = datetime.now().month
        year = datetime.now().year
        message_text = None

        if report_for == 1:
            time_to = datetime.now().strftime('%Y-%m-%d ') + '23:59:59'
            time_from = datetime.now().strftime('%Y-%m-%d ') + '00:00:00'
            report_ = self.db.generate_report(time_from, time_to, call.from_user.id)
            if report_:
                message_text = f'{"-"*50}\nОтчет за день: \n\n{report_}'

        elif report_for == 2:
            time_from = list(week for week in c.monthdatescalendar(year, month) if datetime.now().date() in week)[0][0]
            time_to = list(week for week in c.monthdatescalendar(year, month) if datetime.now().date() in week)[0][-1]
            report_ = self.db.generate_report(time_from, time_to, call.from_user.id)
            if report_:
                message_text = f'{"-"*50}\nОтчет за неделю: \n\n{report_}'

        elif report_for == 3:
            time_from = [day for day in c.itermonthdates(year, month) if day.month == 5][0]
            time_to = [day for day in c.itermonthdates(year, month) if day.month == 5][-1]
            report_ = self.db.generate_report(time_from, time_to, call.from_user.id)
            if report_:
                message_text = f'{"-"*50}\nОтчет за месяц: \n\n{report_}'

        elif exact_month:
            month = int(exact_month.split('_')[0])
            year = int(str(datetime.now().year)[:-1] + exact_month.split('_')[1])

            time_from = [day for day in c.itermonthdates(year, month) if day.month == month][0].strftime(
                '%Y-%m-%d 00:00:00')
            time_to = [day for day in c.itermonthdates(year, month) if day.month == month][-1].strftime(
                '%Y-%m-%d 23:59:59')
            report_ = self.db.generate_report(time_from, time_to, call.from_user.id)
            if report_:
                message_text = f'{"-"*50}\nОтчет за месяц: \n\n{report_}'

        if message_text:
            self.send_message(chat_id=call.message.chat.id,
                              text=message_text)
        else:
            self.send_message(chat_id=call.message.chat.id,
                              text='Нет затрат за этот период')

    def get_report(self, call):
        """Starting the preparation of the report, depending on the user's choice"""

        self.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        report_for = callback_data.get('cat')

        if report_for == 4:
            if 'date' not in callback_data:
                buttons_name = self.db.get_report_month(call.from_user.id)
                self.keyboard(call.message, 'Выберите месяц:', buttons_name, callback_key='date',
                              previous_data=call.data)
            else:
                exact_month = callback_data.get('date')
                self.prepare_report(call, exact_month=exact_month)
        else:
            self.prepare_report(call, report_for)

    def delete_category(self, call):
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        category_name = categories.get(callback_data.get('cat', {})).get('name', 'Name Error')
        if callback_data.get('an'):
            if self.db.delete_category(call.message, callback_data.get('cat')):
                self.send_message(chat_id=call.message.chat.id, text=f'Удалил категорию: {category_name}')
            else:
                self.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')

    def delete_subcategories(self, call):
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        subcategories_dict = categories.get(callback_data.get('cat', ), {}).get('subcategories')
        if not subcategories_dict:
            self.send_message(chat_id=call.message.chat.id, text='Нет подкатегорий')
        elif subcategories_dict and 'sub' not in callback_data:
            data = json.loads(call.data)
            data['af'] = 1
            data['a'] = 2
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            subcategories_dict.items()}
            self.keyboard(call.message, 'Выбери подкатегорию:', buttons_name, callback_key='sub',
                          previous_data=json.dumps(data))
        elif callback_data.get('an'):
            subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')
            if self.db.delete_subcategory(call, callback_data.get('cat'), callback_data.get('sub')):
                self.send_message(chat_id=call.message.chat.id, text=f'Удалил подкатегорию: {subcategory_name}')
            else:
                self.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')

    def ask_again(self, call):
        """Confirmation of the choice made"""

        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        category_name = categories.get(callback_data.get('cat', ), {}).get('name', 'Name Error')
        subcategories_name = categories.get(callback_data.get('cat', ), {}).get('subcategories', {}).get(
            callback_data.get('sub', ), {}).get('name', 'Name Error')
        t = {1: f'Удалить категорию {category_name}?',
             2: f'Удалить подкатегорию {subcategories_name}?'}

        buttons_name = {1: 'Да', 0: 'Нет'}
        self.keyboard(call.message, t.get(callback_data.get('a'), 'Вы уверенны?'), buttons_name,
                      callback_key='an', previous_data=call.data)

    def add_subcategory(self, call):
        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        category_name = categories.get(callback_data.get('cat'), {}).get('name')
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        if self.db.can_add_subcategory(call):
            self.send_message(chat_id=call.message.chat.id, text=f'Категория: {category_name}. '
                                                                 f'Введите новое имя подкатегории:',
                              reply_markup=types.ForceReply())
        else:
            message_text = f'Нельзя добавлять больше {str(self.max_len_category)} подкатегорий!'
            self.send_message(chat_id=call.message.chat.id, text=message_text)

    def callback_inline(self, call):
        """Function selection depending on the button pressed"""

        funcs = {'amount': self.get_amount,
                 'set_stng': self.set_settings_bot,
                 'get_rp': self.get_report,
                 'del': self.delete_category,
                 'dels': self.delete_subcategories,
                 'a': self.ask_again,
                 'add_s': self.add_subcategory,
                 'help': self.help_data}
        try:
            if json.loads(call.data).get('af') and 'an' not in json.loads(call.data):
                self.ask_again(call)
            else:
                func = funcs.get(json.loads(call.data).get('f'), lambda *args, **kwargs: False)
                func(call)
        except Exception as e:
            logging.error(e)

    def text(self, message):
        """Processing text messages from the user and calling certain functions"""

        if message.reply_to_message:
            try:
                self.delete_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
                self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            except:
                pass
            if message.reply_to_message.text.find('Категория') != -1 and message.reply_to_message.text.find(
                    'Сумма:') != -1:
                if message.reply_to_message.text.find(' грн.') != -1:
                    self.send_message(chat_id=message.chat.id,
                                      text='Уже есть')
                else:
                    try:
                        amount = round(float(message.text), 2)
                        if amount < 92233720368547758.07:
                            if self.db.add_data(message):
                                self.send_message(chat_id=message.chat.id,
                                                  text=f'Добавил:\n{message.reply_to_message.text} {message.text} грн.')
                            else:
                                self.send_message(chat_id=message.chat.id,
                                                  text='Видимо у меня проблемы, попробуй позже')

                        else:
                            self.send_message(chat_id=message.chat.id,
                                              text='Это слишком большая сумма.')

                    except:
                        self.send_message(chat_id=message.chat.id,
                                          text='Чет не то с суммой, давай по новой!\n'
                                               'К примеру: 1 грн 55 копеек нужно накисать как 1.55')
                self.add(message)
            if message.reply_to_message.text.find('Вставьте ссылку на вашу Google таблицу:') != -1:
                # Имениьть на set_google_sheet_change
                id_sheet = re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', message.text)
                if id_sheet:
                    self.db.set_google_sheet_id_change(message.from_user.id, id_sheet[0])
                    self.send_message(chat_id=message.chat.id,
                                      text=f'После проверки подключения ссылка изменится на: '
                                           f'https://docs.google.com/spreadsheets/d/{id_sheet[0]}')
                else:
                    self.send_message(chat_id=message.chat.id, text='Что-то не так c сылкой.')

            if message.reply_to_message.text.find('Введите новое имя категории') != -1:
                if message.text.isalpha():
                    if len(message.text) >= self.max_len_category:
                        self.send_message(chat_id=message.chat.id,
                                          text=f'Очень длинное название ')
                    # Длина не больше
                    elif self.db.add_category(message):
                        self.send_message(chat_id=message.chat.id,
                                          text=f'Добавил категорию {message.text}.')
                    else:
                        self.send_message(chat_id=message.chat.id, text='Что-то пошло не так (')
                else:
                    self.send_message(chat_id=message.chat.id,
                                      text='Используйте только буквы для названия категории без пробелов!\n'
                                           'Попробуйте снова.')

            if message.reply_to_message.text.find('Введите новое имя подкатегории:') != -1:
                if message.text.isalpha():
                    if len(message.text) >= self.max_len_subcategory:
                        self.send_message(chat_id=message.chat.id,
                                          text=f'Очень длинное название ')
                    elif self.db.add_subcategory(message):
                        self.send_message(chat_id=message.chat.id,
                                          text=f'Добавил подкатегорию {message.text}.')
                    else:
                        self.send_message(chat_id=message.chat.id,
                                          text='Что-то не так')
                else:
                    self.send_message(chat_id=message.chat.id,
                                      text='Используйте только буквы для названия подкатегории!\n'
                                           'Попробуйте снова.')
        else:
            self.send_message(chat_id=message.chat.id,
                              text='Я не знаю что ты от меня хочешь 🤷🏻‍♂️\n'
                                   'Если нужна помощь, попробуй команду  \help.')


def send_message_telegram(message, chat_id, subject=''):
    """ Sending messages to the user through requests"""

    try:
        config = ConfigParser()
        config.read(os.path.dirname(os.path.abspath(__file__)) + '/app.ini')
        token = config.get('BUDGET_BOT', 'token')
        response = requests.post(
            url='https://api.telegram.org/bot{}/sendMessage'.format(token),
            data={'chat_id': chat_id, 'text': '{}{}'.format(subject, message)}
        ).json()
        if not response['ok']:
            logging.error(f'Error for send message to :{chat_id}. Error: {response.get("description")}')
    except Exception as e:
        logging.error(f'Send message Error.\n Error: {e}')
