# -*- coding: utf-8 -*-
import os
import re
import logging
import requests
import json
import calendar
from datetime import datetime, time, timedelta
from configparser import ConfigParser

import telebot
from telebot import types

from models.users import Data

from database import DB
from monobank_api import set_webhook, get_webhook
from encryption import encrypt


# from databese_new import DB as DB_new


# дописать help_data
# добавить версию приложения

class BudgetBot(telebot.TeleBot):
    def __init__(self):

        self.config = ConfigParser()
        self.config.read(os.path.dirname(os.path.abspath(__file__)) + '/config/app.ini')
        token = self.config.get('BUDGET_BOT', 'token')
        super().__init__(token, threaded=False)

        # database object
        self.db = None

        # maximum number of categories
        self.max_number_categories = None
        # maximum number of subcategories
        self.max_number_subcategories = None

        # maximum length of category name
        self.max_len_category = None
        # maximum length of subcategory name
        self.max_len_subcategory = None
        # maximum length of description for transaction
        self.max_len_description = None

        # email bot to which to open access to the table
        self.email_budget_bot = None

        # chat id where bot error messages are sent
        self.chat_id_error_notification = None

        # Budget_Bot host
        self.host = None

        # Version of api client monobank
        self.monobank_api_version = None

        # Superusers ids
        self.superusers = None

        self.set_settings()

    def set_settings(self):
        self.db = DB()
        self.max_number_categories = self.config.get('BUDGET_BOT', 'max_number_categories')
        self.max_number_subcategories = self.config.get('BUDGET_BOT', 'max_number_subcategories')
        self.max_len_category = self.config.getint('BUDGET_BOT', 'max_len_category')
        self.max_len_subcategory = self.config.getint('BUDGET_BOT', 'max_len_subcategory')
        self.max_len_description = self.config.getint('BUDGET_BOT', 'max_len_description')

        self.email_budget_bot = self.config.get('SHEETS_API', 'email_budget_bot')
        self.chat_id_error_notification = self.config.getint('BUDGET_BOT', 'chat_id_error_notification')

        self.host = self.config.get('FLASK', 'webhook_host')
        self.monobank_api_version = self.config.get('BUDGET_BOT', 'monobank_api_version')

        self.superusers = [int(user_id) for user_id in
                           self.config.get('BUDGET_BOT', 'superusers').split(',')]

    def ping(self, message):
        logging.error('ping OK')
        self.send_message(chat_id=message.chat.id, text='Привет 👋\n Я работаю 😎')

    def start(self, message):
        """Adding a user to the database and welcome with user"""

        user_name = message.from_user.first_name
        user_name = '' if not user_name or user_name == 'None' else f', {user_name} '
        if not self.db.is_user(message.from_user.id):
            if self.db.add_user(message):
                message_text = f'Здравствуйте{user_name}👋\nBudget Bot поможет Вам контролировать Ваш бюджет 💸\n' + \
                               'Все доходы и расходы будут записываться в Вашу персональную Google Таблицу 😎\n' \
                               'Вы можете строить любые графики, таблицы или делать расчеты благодаря данным, ' \
                               'которые будут в неё автоматически добавляться.\n' \
                               'Используя Budget Bot вы подтверждаете что согласны с условиями пользовательского ' \
                               'соглашения: https://budgetbot.site/agreement.\n' \
                               'Для того чтоб получить больше информации используй команду \help.\n\n' \
                               'И напоследок цитата Дэйва Рэмси:\n' \
                               '«Или ты будешь управлять своими деньгами, или их отсутствие будет управлять тобой.»'
                self.send_message(chat_id=message.chat.id, text=message_text)
        else:
            message_text = f'И снова привет{user_name}👋\nЕсли Вам нужна помощь используй команду \help.'
            self.send_message(chat_id=message.chat.id, text=message_text)

    def add(self, message):
        """Select categories"""

        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'am'})
        categories = self.db.get_category(message.from_user.id)
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        self.keyboard(message.chat.id, 'Выбери категорию:', buttons_name, callback_key='ct', previous_data=data)

    def settings(self, message):
        """Select Settings categories"""

        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'set_stng'})
        buttons_name = {1: 'Добавить', 2: 'Удалить', 3: 'Получить ссылку на Google таблицу',
                        4: 'Изменить ссылку на Google таблицу', 5: 'Оповещения от Monobank', 6: 'Установить баланс'}
        self.keyboard(message.chat.id, 'Выбери настройки:', buttons_name, callback_key='ct', previous_data=data,
                      qt_key=1, )

    def report(self, message):
        """Select report categories"""

        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'get_rp'})
        buttons_name = {1: 'День', 2: 'Неделя', 3: 'Месяц', 4: 'Определенный месяц', 5: 'Получить баланс'}
        self.keyboard(message.chat.id, 'Отчет за:', buttons_name, callback_key='ct', previous_data=data, qt_key=1, )

    def help(self, message):
        """Select categories for help the user"""

        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'help'})
        buttons_name = {
            1: 'Для чего нужен Budget Bot?',
            2: 'Что он может?',
            3: 'Для чего нужна гугл таблица?',
            4: 'Для чего нужна команда “/add”?',
            5: 'Для чего нужна команда “/report”?',
            6: 'Для чего нужна команда “/settings”?',
            7: 'Для чего нужна команда “/help”?',
            8: 'Как переключиться на свою гугл таблицу?',
            9: 'Как установить оповещения от Monobank?',
            10: 'Получить данные для тех поддержки',
            11: {'name': 'Подробнее на сайте', 'url': 'https://budgetbot.site/'},
            12: {'name': 'Пользовательское соглашение', 'url': 'https://budgetbot.site/agreement'},
        }
        self.keyboard(message.chat.id, 'Выберите категорию:', buttons_name, callback_key='id', previous_data=data,
                      qt_key=1)

    def get_command_token(self, message):
        token = encrypt(f'user_id:{message.from_user.id};chat_id:{message.chat.id}')
        self.send_message(chat_id=message.chat.id, text=f'Ваш токен:\n{token}')

    def simple_commands(self, message=None, command=None, user_id=None):
        if message:
            pass
        elif command and user_id:
            answer = self.db.simple_commands(user_id, command)
            return answer

    def add_card(self, message):
        self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        data = json.dumps({'f': 'addc'})
        buttons_name = {1: 'Monobank', 2: 'PrivatBank'}
        self.keyboard(message.chat.id, 'Отчет за:', buttons_name, callback_key='ct', previous_data=data, qt_key=1, )

    def help_data(self, call):
        """Sending help to the user"""

        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        all_messages = {
            1: 'Budget Bot - телегам бот предназначенный, для того чтоб помочь Вам управлять своим бюджетом.',
            2: 'Ваши транзакции записываются в Вашу Google таблицу в которой строятся различные таблицы и графики. Вы можете изменять таблицу как пожелаете или использовать стандартную Google таблицу, которая будет создана для Вас. При этом в Budget Bot есть команды, которые пришлют вам в телеграм стандартный отчет за месяц, день или неделю. Также Вы всегда можете посмотреть ваш общий баланс. Кроме этого Вы можете установить уведомления от банка, и при любой транзакции они будут автоматически приходить в Budget Bo',
            3: 'В Google таблицу будут записываться все ваши транзакции, которые вы будете добавлять через Budget Bot. Эти транзакции добавляются в лист Data, а затем строятся различные графики и таблицы. Когда вы начинаете пользоваться ботом то для Вас автоматически создается персональная Google таблица. Внимание: доступ к Google таблице осуществляется по уникальной ссылке, не передавайте эту ссылку третьим лицам.',
            4: 'Используя команду “/add” вы можете добавить новые транзакции. Также можете добавлять описание транзакции или устанавливать дату транзакции.',
            5: 'Используя команду “/report” вы можете получить отчет по доходам/расходам за текущий день, неделю или месяц. Также вы можете получить за любой месяц по транзакциям которые на старше одного года. Здесь же вы можете посмотреть ваш текущий баланс.',
            6: 'Используя команду “/settings” Вы можете настраивать свой Budget Bot. Изменять категории и подкатегории, изменять и получать Вашу Google таблицу, устанавливать ваш общий баланс, устанавливать оповещения от банка и др.',
            7: 'Используя команду “/help” Вы можете получить краткие сведения для работы с Budget Bot и различную информацию.',
            8: 'Для переключение таблицы используйте команду “/settings” > “Изменить ссылку на Google таблицу” > открыть доступ на редактирование таблицы для пользователя и нажать “Да” > вставить Вашу ссылку на Google таблицу и отправить сообщение.',
            9: 'Используя команду “/settings” > “Оповещения от Monobank” > “Установить оповещения” > на ноутбуке перейдите по ссылке https://api.monobank.ua/ > сканируйте телефоном QR код и подтвердите в приложении Monobank > скопруйте Ваш токен > нажмите в боте “Установить” > Вставьте ваш токен и отправьте сообщение.',
            10: 'Telegram: @sviatoslav_pereverziev Почта: sviatoslav.pereverziev@gmail.com Телефон: +380 63 920 66 97', }
        messages_id = int(callback_data.get('id'))
        message_text = all_messages.get(messages_id)
        if message_text:
            self.send_message(chat_id=call.message.chat.id, text=message_text)

    def get_amount(self, call):
        """Function to add income and expenses"""

        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        subcategories_dict = categories.get(callback_data.get('ct', ), {}).get('subcategories', {})
        if callback_data.get('ct') == 99:
            self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            return

        if subcategories_dict and 'sub' not in callback_data:
            self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            subcategories_dict.items()}
            self.keyboard(call.message.chat.id, 'Выберите подкатегорию:', buttons_name, callback_key='sub',
                          previous_data=call.data, add_cancel=False)
        else:
            category_name = categories.get(callback_data.get('ct'), {}).get('name')
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

    def add_from_api(self, call=None, user_id=None, chat_id=None, id=None, message_text=None, data_api=None):
        transaction_id = None
        if data_api:
            transaction_id = self.db.add_data_from_api(data_api)
            if not transaction_id:
                return False

        if data_api and transaction_id:
            data = json.dumps({'f': 'afa', 'id': transaction_id})
            categories = self.db.get_category(data_api['user_id'])
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            categories.items()}
            currency = {980: 'грн', 840: '$', 978: '€'}.get(data_api['currency_code'])
            sign = '-' if not data_api['is_income'] else ''
            message_text = f'Банк: {data_api["bank"]}\n' \
                           f'Сумма: {sign}%.2f {currency}.\n' % float(data_api['amount'] / 100)
            if data_api['description']:
                message_text += 'Описание: %s.\n' % data_api['description']
            if data_api['commission'] > 0:
                message_text += f'Коммисия: %.2f {currency}.\n' % float(data_api['commission'] / 100)
            if data_api['cashback'] > 0:
                message_text += f'Кэшбэк: %.2f {currency}.\n' % float(data_api['cashback'] / 100)
            message_text += f'Баланс карты: %.2f {currency}.\nВыберете категорию:\n' % float(
                data_api['card_balance'] / 100)

            self.keyboard(data_api['chat_id'], message_text, buttons_name, 'ct', data)

        if call:
            callback_data = json.loads(call.data)
            if callback_data.get('ct', ) == 99:
                self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                return
            categories = self.db.get_category(call.from_user.id)
            subcategories_dict = categories.get(callback_data.get('ct', ), {}).get('subcategories', {})
            category_name = categories.get(callback_data.get('ct'), {}).get('name')
            self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            if subcategories_dict and 'sub' not in callback_data:
                message_text = call.message.text.replace('\nВыберете категорию:', '')
                buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                                subcategories_dict.items()}
                message_text = f'{message_text}\nКатегория: {category_name}.\nВыберете подкатегорию:'
                self.keyboard(call.message.chat.id, message_text, buttons_name, callback_key='sub',
                              previous_data=call.data, add_cancel=False)
            else:

                subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')
                if subcategories_dict:
                    subcategory_text = f'\nПодкатегория: {subcategory_name}. '
                else:
                    subcategory_text = ''

                message_text = call.message.text.replace('\nВыберете подкатегорию:', '').replace(
                    '\nВыберете категорию:', '')
                if 'Категория: ' not in message_text:
                    message_text += '\nКатегория: %s' % category_name
                message_text += subcategory_text
                transaction_id = callback_data.get('id')
                amount = self.db.get_amount_transaction(transaction_id)
                self.db.update_balance(call.from_user.id, abs(amount), amount > 0)
                self.db.set_category(transaction_id, category_name)
                if subcategory_name and subcategory_name != 'Name Error':
                    self.db.set_subcategory(transaction_id, subcategory_name)
                balance = self.db.get_balance(call.from_user.id)
                self.db.set_balance_transaction(transaction_id, balance)
                self.db.set_transaction_status(transaction_id, 1)
                message_text = f'Добавил:\n{message_text}\nБаланс: {balance / 100} грн.'
                self.send_message(chat_id=call.message.chat.id, text=message_text)

    def set_settings_bot(self, call):
        """Setting user preferences"""

        # self.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        func_id = callback_data.get('ct')
        if func_id == 1:
            buttons_name = {11: 'Категорию', 12: 'Подкатегорию', }
            self.keyboard(call.message.chat.id, 'Добавить:', buttons_name, callback_key='ct', previous_data=call.data, )
        elif func_id == 2:
            buttons_name = {21: 'Категорию', 22: 'Подкатегорию', }
            self.keyboard(call.message.chat.id, 'Удалить:', buttons_name, callback_key='ct', previous_data=call.data, )
        elif func_id == 3:
            sheets_id = self.db.get_google_sheets_id(call.from_user.id)
            if sheets_id is None:
                self.send_message(chat_id=call.message.chat.id, text='Ссылка на Google таблицу не установлена.')
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
                               f'{self.email_budget_bot}\n Вы открыли доступ?'
                self.keyboard(call.message.chat.id, message_text, buttons_name, callback_key='yes',
                              previous_data=call.data, add_cancel=False)
            elif not callback_data.get('yes'):
                message_text = 'Для того чтоб получить больше информации о том, как изменить Google таблицу ' \
                               'и открыть доступ введите команду \help и перейдите в ' \
                               '"Как переключиться на свою гугл таблицу?".'
                self.send_message(chat_id=call.message.chat.id, text=message_text)
        elif func_id == 5:
            buttons_name = {51: 'Установить оповещения', 52: 'Отключить оповещения', 53: 'Проверить оповещения',
                            54: 'Больше информации об оповещениях Monobank'}
            self.keyboard(call.message.chat.id, 'Выберите действие:', buttons_name, callback_key='ct',
                          previous_data=call.data)

        elif func_id == 6:
            message_text = 'Введите сумму вашего баланса:'
            self.send_message(chat_id=call.message.chat.id, text=message_text,
                              reply_markup=types.ForceReply())

        elif func_id == 11:
            if self.db.can_add_category(call.from_user.id):
                buttons_name = {31: 'Доходы', 32: 'Расходы', }
                self.keyboard(call.message.chat.id, 'Выберите тип категории:', buttons_name, callback_key='ct',
                              previous_data=call.data, add_cancel=False)
            else:
                message_text = f'Нельзя добавлять больше {self.max_number_categories} категорий.'
                self.send_message(chat_id=call.message.chat.id, text=message_text)

        elif func_id == 12:
            categories = self.db.get_category(call.from_user.id)

            data = json.dumps({'f': 'add_s'})
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            categories.items()}
            self.keyboard(call.message.chat.id, 'Выберите категорию:', buttons_name, callback_key='ct',
                          previous_data=data)
        elif func_id == 21:
            categories = self.db.get_category(call.from_user.id)

            data = json.dumps({'f': 'del', 'af': 1, 'a': 1})
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            categories.items()}
            self.keyboard(call.message.chat.id, 'Удалить категорию:', buttons_name, callback_key='ct',
                          previous_data=data)
        elif func_id == 22:
            categories = self.db.get_category(call.from_user.id)
            data = json.dumps({'f': 'dels'})
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            categories.items()}
            self.keyboard(call.message.chat.id, 'Выберите категорию:', buttons_name, callback_key='ct',
                          previous_data=data)
        elif func_id == 31 or func_id == 32:
            self.send_message(chat_id=call.message.chat.id,
                              text='Введите новое имя категории {}:'.format(
                                  'доходов' if func_id == 31 else 'расходов'),
                              reply_markup=types.ForceReply())
        elif func_id == 51:
            message_text = 'Устанавка оповещения Monobank означает ваше согласие с условиями пользовательского соглашения: ' \
                           'https://budgetbot.site/agreement.\nПерейдите по ссылке https://api.monobank.ua/, ' \
                           'авторизируйтесь и скопируйте токен.'
            buttons_name = {55: 'Установить'}
            self.keyboard(call.message.chat.id, message_text, buttons_name, callback_key='ct',
                          previous_data=call.data)

        elif func_id == 52:
            message_text = 'Перейдите по ссылке https://api.monobank.ua/, авторизируйтесь и скопируйте токен.\nВставьте ваш токен для отмены оповещений:'
            self.send_message(chat_id=call.message.chat.id, text=message_text, reply_markup=types.ForceReply())

        elif func_id == 53:
            message_text = 'Перейдите по ссылке https://api.monobank.ua/, авторизируйтесь и скопируйте токен.\nВставьте ваш токен для проверки оповещений:'
            self.send_message(chat_id=call.message.chat.id, text=message_text, reply_markup=types.ForceReply())

        elif func_id == 54:
            message_text = 'Вы можете установить оповещения от Monobank и все траты и доходы с ' \
                           'монобанка будут автоматически приходить в Budget Bot.\n' \
                           'Для получения большего количества информации используйте команды \help'
            self.send_message(chat_id=call.message.chat.id, text=message_text)

        elif func_id == 55:
            message_text = 'Вставьте полученный токен:'
            self.send_message(chat_id=call.message.chat.id, text=message_text, reply_markup=types.ForceReply())

    def prepare_report(self, call, report_for=None, exact_month=None):
        print('prepare_report')
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

        # day
        if report_for == 1:
            time_from = datetime.combine(datetime.today(), time.min)
            time_to = datetime.combine(datetime.today(), time.min) + timedelta(days=1)
            report_ = self.db.generate_report(time_from, time_to, call.from_user.id)
            if report_:
                message_text = f'{"-" * 38}\nОтчет за день: \n\n{report_}'

        # week
        elif report_for == 2:
            time_from = list(week for week in c.monthdatescalendar(year, month) if datetime.now().date() in week)[0][0]
            time_to = list(week for week in c.monthdatescalendar(year, month) if datetime.now().date() in week)[0][-1]
            report_ = self.db.generate_report(time_from, time_to, call.from_user.id)
            if report_:
                message_text = f'{"-" * 38}\nОтчет за неделю: \n\n{report_}'

        # month
        elif report_for == 3 or exact_month:
            if exact_month:
                month = int(exact_month.split('_')[0])
                year = int(str(datetime.now().year)[:-2] + exact_month.split('_')[1])
            month_name = Data.CALENDER_MONTH.get(month, 'месяц')
            time_from = [day for day in c.itermonthdates(year, month) if day.month == month][0]
            time_to = time_from + timedelta(days=calendar.monthrange(year, month)[1])
            report_ = self.db.generate_report(time_from, time_to, call.from_user.id)
            if report_:
                message_text = f'{"-" * 38}\nОтчет за {month_name}: \n\n{report_}'

        if message_text:
            self.send_message(chat_id=call.message.chat.id,
                              text=message_text)
        else:
            self.send_message(chat_id=call.message.chat.id,
                              text='За этот период нет транзакций.')

    def get_report(self, call):
        """Starting the preparation of the report, depending on the user's choice"""

        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        report_for = callback_data.get('ct')

        if report_for == 4:
            if 'date' not in callback_data:
                buttons_name = self.db.get_report_month(call.from_user.id)
                if not buttons_name:
                    self.send_message(chat_id=call.message.chat.id, text=f'У вас нет затрат.')
                else:
                    self.keyboard(call.message.chat.id, 'Выберите месяц:', buttons_name, callback_key='date',
                                  previous_data=call.data, add_cancel=False)
            else:
                exact_month = callback_data.get('date')
                self.prepare_report(call, exact_month=exact_month)
        elif report_for == 5:
            balance = self.db.get_balance(call.from_user.id)
            self.send_message(chat_id=call.message.chat.id,
                              text=f'Баланс: {balance / 100} грн.')

        elif report_for != 99:
            self.prepare_report(call, report_for)

    def delete_category(self, call):
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        if callback_data.get('ct') == 99:
            self.send_message(chat_id=call.message.chat.id, text='Нельзя удалить категорию.')
            return
        categories = self.db.get_category(call.from_user.id)
        category_name = categories.get(callback_data.get('ct', {})).get('name', 'Name Error')

        if callback_data.get('an'):
            if self.db.delete_category(call.from_user.id, callback_data.get('ct')):
                self.send_message(chat_id=call.message.chat.id, text=f'Удалил категорию: {category_name}')
            else:
                self.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')

    def delete_subcategories(self, call):
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        subcategories_dict = categories.get(callback_data.get('ct', ), {}).get('subcategories')
        if not subcategories_dict:
            self.send_message(chat_id=call.message.chat.id, text='Нет подкатегорий')
        elif subcategories_dict and 'sub' not in callback_data:
            data = json.loads(call.data)
            data['af'] = 1
            data['a'] = 2
            buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                            subcategories_dict.items()}
            self.keyboard(call.message.chat.id, 'Выбери подкатегорию:', buttons_name, callback_key='sub',
                          previous_data=json.dumps(data), add_cancel=False)

        elif callback_data.get('an'):
            subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')

            if self.db.delete_subcategory(call.from_user.id, callback_data.get('ct'), callback_data.get('sub')):
                self.send_message(chat_id=call.message.chat.id, text=f'Удалил подкатегорию: {subcategory_name}')
            else:
                self.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')

    def ask_again(self, call):
        """Confirmation of the choice made"""

        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        callback_data = json.loads(call.data)
        categories = self.db.get_category(call.from_user.id)
        category_name = categories.get(callback_data.get('ct', ), {}).get('name', 'Name Error')
        subcategories_name = categories.get(callback_data.get('ct', ), {}).get('subcategories', {}).get(
            callback_data.get('sub', ), {}).get('name', 'Name Error')
        t = {1: f'Удалить категорию {category_name}?',
             2: f'Удалить подкатегорию {subcategories_name}?'}

        buttons_name = {1: 'Да', 0: 'Нет'}
        self.keyboard(call.message.chat.id, t.get(callback_data.get('a'), 'Вы уверенны?'), buttons_name,
                      callback_key='an', previous_data=call.data, add_cancel=False)

    def add_subcategory(self, call):
        callback_data = json.loads(call.data)
        self.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        if callback_data.get('ct') == 99:
            self.send_message(chat_id=call.message.chat.id, text='Нельзя добавить подкатегорию.')
            return
        categories = self.db.get_category(call.from_user.id)
        category_name = categories.get(callback_data.get('ct'), {}).get('name')
        if self.db.can_add_subcategory(call):
            self.send_message(chat_id=call.message.chat.id, text=f'Категория: {category_name}. '
                                                                 f'Введите новое имя подкатегории:',
                              reply_markup=types.ForceReply())
        else:
            message_text = f'Нельзя добавлять больше {self.max_number_subcategories} подкатегорий.'
            self.send_message(chat_id=call.message.chat.id, text=message_text)

    def callback_inline(self, call):
        """Function selection depending on the button pressed"""

        funcs = {'am': self.get_amount,
                 'set_stng': self.set_settings_bot,
                 'get_rp': self.get_report,
                 'del': self.delete_category,
                 'dels': self.delete_subcategories,
                 'a': self.ask_again,
                 'add_s': self.add_subcategory,
                 'help': self.help_data,
                 'afa': self.add_from_api}
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
            self.delete_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
            self.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            if message.reply_to_message.text.find('Категория') != -1 and message.reply_to_message.text.find(
                    'Сумма:') != -1:
                if message.reply_to_message.text.find(' грн.') != -1:
                    self.send_message(chat_id=message.chat.id,
                                      text='Уже есть')
                else:
                    try:
                        message_amount = re.findall(r'\d+[.]\d+|\d+', message.text)[0]
                        amount = abs(int(round(float(message_amount), 2) * 100))
                        if amount < 9223372036854775807:

                            date = ''
                            patterns = [r'\d{2}[.]\d{2}[.]\d{2}\s\d{2}[:]\d{2}', r'\d{2}[.]\d{2}[.]\d{2}']
                            for pattern in patterns:
                                if re.findall(pattern, message.text):
                                    date = re.findall(pattern, message.text)[0]
                                    break

                            description = message.text.replace(date, '').replace(str(message_amount), '').strip()

                            if date:
                                if len(date) == 8:
                                    date += ' 12:00'
                                try:
                                    date = datetime.strptime(date, '%d.%m.%y %H:%M')
                                except ValueError:
                                    self.send_message(chat_id=message.chat.id,
                                                      text='Неправильная дата.\n'
                                                           'Формат даты %d.%m.%y %H:%M или %d.%m.%y')
                                    return

                            if description and len(description) > self.max_len_description:
                                self.send_message(chat_id=message.chat.id,
                                                  text='Слишком большая длина описания.')
                                return

                            balance = self.db.add_data(message, description, date=date)
                            if balance:
                                message_text = f'Добавил:\n{message.reply_to_message.text} {message_amount} грн.'
                                if description:
                                    message_text += f'\nОписание: {description}.'
                                if balance and not date:
                                    message_text += f'\nБаланс: {balance / 100} грн.'
                                if date:
                                    message_text += f'\nДата: {date.strftime("%d.%m.%y %H:%M.")}'
                                self.send_message(chat_id=message.chat.id,
                                                  text=message_text)
                            else:
                                self.send_message(chat_id=message.chat.id,
                                                  text='Видимо у меня проблемы, попробуй позже')

                        else:
                            self.send_message(chat_id=message.chat.id,
                                              text='Это слишком большая сумма.')

                    except ValueError as e:

                        self.send_message(chat_id=message.chat.id,
                                          text=f'Чет не то с суммой, давай по новой!\n'
                                               f'Error {e}'
                                               'К примеру: 1 грн 55 копеек нужно накисать как 1.55')
                    except Exception as e:
                        logging.error(f'Error: {e}')
                        self.send_message(chat_id=message.chat.id,
                                          text='Видимо у меня проблемы, попробуй позже')

                self.add(message)
            elif message.reply_to_message.text.find('Вставьте ссылку на вашу Google таблицу:') != -1:
                id_sheet = re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', message.text)
                if id_sheet:
                    self.db.set_google_sheet_id_change(message.from_user.id, id_sheet[0])
                    self.send_message(chat_id=message.chat.id,
                                      text=f'После проверки подключения ссылка изменится на: '
                                           f'https://docs.google.com/spreadsheets/d/{id_sheet[0]}')
                else:
                    self.send_message(chat_id=message.chat.id, text='Что-то не так c сылкой.')

            elif message.reply_to_message.text.find('Введите новое имя категории') != -1:
                if len(message.text) >= self.max_len_category:
                    self.send_message(chat_id=message.chat.id,
                                      text=f'Очень длинное название ')
                elif self.db.add_category(message):
                    self.send_message(chat_id=message.chat.id,
                                      text=f'Добавил категорию {message.text}.')
                else:
                    self.send_message(chat_id=message.chat.id, text='Что-то пошло не так (')

            elif message.reply_to_message.text.find('Введите новое имя подкатегории:') != -1:
                if len(message.text) >= self.max_len_subcategory:
                    self.send_message(chat_id=message.chat.id,
                                      text=f'Очень длинное название ')
                elif self.db.add_subcategory(message):
                    self.send_message(chat_id=message.chat.id,
                                      text=f'Добавил подкатегорию {message.text}.')
                else:
                    self.send_message(chat_id=message.chat.id,
                                      text='Что-то не так')

            elif message.reply_to_message.text.find('Вставьте ваш токен для проверки оповещений:') != -1:
                token = message.text.split(':')[-1].strip()
                if token:
                    webhook = get_webhook(token)
                    if webhook and webhook != 'Token Error':
                        if webhook.rfind('https://%s/monobank_api/%s/' % (self.host, self.monobank_api_version)) == -1:
                            message_text = f'Неверный webhook. У вас установлен webhook: {webhook}.\n' \
                                           f'Установите оповещения от monobank в настройках еще раз или ' \
                                           f'напишите в техподдержку'
                        else:
                            message_text = 'Уведомления включены.'
                    elif webhook and webhook == 'Token Error':
                        message_text = 'Неверный токен.'
                    else:
                        message_text = 'Уведомления отключены.'
                else:
                    message_text = 'Токен не определен. Попробуйте еще раз или напишите в техподдержку.'

                self.send_message(chat_id=message.chat.id, text=message_text)

            elif message.reply_to_message.text.find('Вставьте ваш токен для отмены оповещений:') != -1:
                token = message.text.split(':')[-1].strip()
                if token:
                    response = set_webhook(token, '')
                    message_text = 'Видимо у меня проблемы, попробуй позже'
                    if isinstance(response, dict):
                        if response.get('status') == 'ok':
                            message_text = 'Уведомления отключены.'
                        elif 'errorDescription' in response:
                            if response['errorDescription'] == "Unknown 'X-Token'":
                                message_text = 'Неверный токен.'
                            else:
                                message_text = 'Возникла ошибка при запросе к monobank.\n' \
                                               'Попробуйте еще раз или напишите в техподдержку.'
                else:
                    message_text = 'Токен не определен.\nПопробуйте еще раз или напишите в техподдержку.'

                self.send_message(chat_id=message.chat.id, text=message_text)

            elif message.reply_to_message.text.find('Вставьте полученный токен:') != -1:
                token = message.text.replace('Вставьте полученный токен:', '')
                if token:
                    url = 'https://budgetbot.site/monobank_api/v1/' + encrypt(
                        f'user_id:{message.from_user.id};chat_id:{message.chat.id}')
                    response = set_webhook(token, url)
                    if isinstance(response, dict):
                        if response.get('status') == 'ok':
                            self.send_message(chat_id=message.chat.id, text='Уведомления установлены.')
                        if 'errorDescription' in response:
                            if response['errorDescription'] == "Unknown 'X-Token'":
                                message_text = 'Неверный токен.'
                                self.send_message(chat_id=message.chat.id, text=message_text)
                            else:
                                message_text = 'Видимо у меня проблемы, попробуй позже'
                                self.send_message(chat_id=message.chat.id, text=message_text)

            elif message.reply_to_message.text == 'Введите сумму вашего баланса:':
                try:
                    amount = int(float(message.text) * 100)
                    if abs(amount) < 9223372036854775807:
                        if self.db.set_balance(message.from_user.id, amount):
                            self.send_message(chat_id=message.chat.id,
                                              text=f'Баланс установлен.\nБаланс: {message.text} грн.')
                        else:
                            self.send_message(chat_id=message.chat.id,
                                              text='Видимо у меня проблемы, попробуй позже')

                    else:
                        self.send_message(chat_id=message.chat.id,
                                          text='Это слишком большая сумма.')
                except ValueError as e:
                    self.send_message(chat_id=message.chat.id,
                                      text=f'Чет не то с суммой, давай по новой!\n'
                                           'К примеру: 1 грн 55 копеек нужно накисать как 1.55')

        else:
            self.send_message(chat_id=message.chat.id,
                              text='Я не знаю что Вы от меня хотите 🤷🏻‍♂️\n'
                                   'Если нужна помощь, попробуй команду  \help.')

    def keyboard(self, chat_id, message_text, buttons, callback_key, previous_data, qt_key=3, add_cancel=True):
        """
        Keyboard for all methods

        Args:
            chat_id (int): id chat
            message_text (str): Text above the keyboard
            buttons (dict): Dictionary of buttons, where the key is the button identifier
            and the value is the name of the button
            callback_key (str): Key for keyback button
            previous_data (json): The date that came and is completed by the callback
            qt_key (int): Number of buttons in a row
            add_cancel (bool): Add cancel button

        """

        callback = json.loads(previous_data, encoding='utf-8')
        if add_cancel:
            buttons.update({99: 'Отмена'})
        list_keys = []
        keyboard = types.InlineKeyboardMarkup(row_width=qt_key)
        for button_id, button_name in buttons.items():
            callback[callback_key] = button_id
            callback_data_ = json.dumps(callback)
            if not isinstance(button_name, dict):
                list_keys.append(types.InlineKeyboardButton(button_name, callback_data=callback_data_))
            else:
                list_keys.append(types.InlineKeyboardButton(button_name.get('name'), url=button_name.get('url'),
                                                            callback_data=callback_data_))
        keyboard.add(*list_keys)
        self.send_message(int(chat_id), message_text, reply_markup=keyboard)

    def delete_message(self, chat_id, message_id):
        try:
            return super().delete_message(chat_id, message_id)
        except:
            pass


def send_message_telegram(message, chat_id, subject=''):
    """ Sending messages to the user through requests"""

    try:
        config = ConfigParser()
        config.read(os.path.dirname(os.path.abspath(__file__)) + '/config/app.ini')
        token = config.get('BUDGET_BOT', 'token')
        response = requests.post(
            url='https://api.telegram.org/bot{}/sendMessage'.format(token),
            data={'chat_id': chat_id, 'text': '{}{}'.format(subject, message)}
        ).json()
        if not response['ok']:
            logging.error(f'Error for send message to :{chat_id}. Error: {response.get("description")}')
    except Exception as e:
        logging.error(f'Send message Error.\n Error: {e}')


if __name__ == '__main__':
    b = BudgetBot()
    # header = {'accept': 'application/json', 'Content-Type': 'application/json', }
    # response = requests.post(
    #     'https://budgetbot.site/monobank_api/v1/gAAAAABdvYjzLHsjflizmVujBOBrw5Ld804qsbF00Tl6uFtzjmQUPWWZ1b6LXo70ecMj9XAkyWhjMbqu26r2Lgu2jCCDhSdhICwGDodSMmaSsuuuNL2axtmg7WewXAFaqW52Ogj_PW1g',
    #     data=json.dumps({'type': 'webhook_test'}), headers=header)
    # response = json.loads(response.content, encoding='utf-8')
    # if isinstance(response, dict) and response.get('webhook_test'):
    #     print('OK')
    # b.add_from_api()
    #
    # b.add_from_api('')
    #
    # b.process_new_updates()
