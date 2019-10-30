# -*- coding: utf-8 -*-
import os
import re
import json
import psycopg2
import logging
from configparser import ConfigParser
from datetime import datetime, timedelta
import telebot


# дописать комментарии
# удалить лишнее
# обновлять дату при запросах:


class DB:
    """Class to work with Budget Bot database"""

    # category is a dictionary which contains all basic categories and subcategories
    # the key is the category id
    # id/name this category name
    # id/is_income shows whether this category is income if not then it is an expense
    # id/subcategories this is a dictionary of subcategories in which the key is a category id
    # id/subcategories/name subcategory name
    category = {
        1: {'name': 'Продукты', 'subcategories': {}, 'is_income': False},
        2: {'name': 'Заведения',
            'subcategories': {1: {'name': 'Кафе и рестораны'}, 2: {'name': 'Суши'}, 3: {'name': "McDonalds"}},
            'is_income': False},
        3: {'name': 'Жильё', 'subcategories': {1: {'name': 'Аренда'}, 2: {'name': 'Комуналка'}}, 'is_income': False},
        4: {'name': 'Транспорт', 'subcategories': {
            1: {'name': 'Метро'}, 2: {'name': 'Маршрутка'}, 3: {'name': 'Такси'},
            4: {'name': 'Бензин'}}, 'is_income': False},
        5: {'name': 'Здоровье', 'subcategories': {}, 'is_income': False},
        6: {'name': 'Одежда',
            'subcategories': {1: {'name': 'Одежда'}, 2: {'name': 'Обувь'}, 3: {'name': 'Уход за одеждой'},
                              4: {'name': 'Прочее'}}, 'is_income': False},
        7: {'name': 'Гигиена', 'subcategories': {}, 'is_income': False},
        8: {'name': 'Отдых', 'subcategories': {}, 'is_income': False},
        9: {'name': 'Спорт', 'subcategories': {}, 'is_income': False},
        10: {'name': 'Связь', 'subcategories': {1: {'name': 'Мобильный'}, 2: {'name': 'Интернет'}, },
             'is_income': False},
        11: {'name': 'Техника', 'subcategories': {}, 'is_income': False},
        12: {'name': 'Счета', 'subcategories': {}, 'is_income': False},
        13: {'name': 'Доходы', 'subcategories': {
            1: {'name': 'Зарплата'}, 2: {'name': 'Прибыль'}, 3: {'name': 'Рента'}}, 'is_income': True},
    }

    def __init__(self, ):
        self.config = ConfigParser()
        self.config.read(os.path.dirname(os.path.abspath(__file__)) + '/config/app.ini')

        try:
            self.connection = psycopg2.connect(database=self.config.get('DATABASE', 'database'),
                                               host=self.config.get('DATABASE', 'db_host'),
                                               user=self.config.get('DATABASE', 'db_user'),
                                               password=self.config.get('DATABASE', 'db_password'),
                                               port='5432',
                                               )
            self.connection.set_client_encoding("utf-8")
            self.connection.autocommit = True
        except Exception as e:
            logging.error(e)

        self.max_number_categories = self.config.getint('BUDGET_BOT', 'max_number_categories')
        self.max_number_subcategories = self.config.getint('BUDGET_BOT', 'max_number_subcategories')
        self.calendar_month = {
            1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Августу',
            9: 'Сентабрь',
            10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
        }

    def __enter__(self):
        return self.connection.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()

    @staticmethod
    def _create_table_users():
        query = """
            CREATE TABLE budget_bot_users (
            user_id INTEGER PRIMARY KEY ,
            chat_id INTEGER,
            date_create TIMESTAMP,
            date_update TIMESTAMP,
            sheet_id TEXT,
            category JSON,
            balance BIGINT DEFAULT 0,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            language_code TEXT,
            is_bot BOOL,
            data_sheet_id TEXT,
            sheet_id_change TEXT);"""

        with DB() as db:
            db.execute(query)

    @staticmethod
    def _create_table_data():
        query = """
            CREATE TABLE budget_bot_data (
            id SERIAL PRIMARY KEY,
            message_id INTEGER ,
            user_id INTEGER REFERENCES budget_bot_users (user_id) ON DELETE RESTRICT,
            chat_id INTEGER,
            transaction_id TEXT UNIQUE,
            merchant_id TEXT,
            date_create TIMESTAMP,
            date_update TIMESTAMP,
            category TEXT,
            subcategory TEXT,
            amount BIGINT,
            commission BIGINT,
            cashback BIGINT,
            currency_code SMALLINT,
            is_income BOOL,
            description TEXT,
            status SMALLINT,
            type TEXT,
            card_balance BIGINT,
            balance BIGINT DEFAULT 0,
            message_text TEXT, 
            is_add_in_sheet BOOL DEFAULT FALSE,
            add_in_sheet_id TEXT,
            date_add_in_sheet TIMESTAMP);"""

        with DB() as db:
            db.execute(query)

    @staticmethod
    def _create_table_cards():
        query = """
                CREATE TABLE budget_bot_cards (
                id SERIAL PRIMARY KEY,
                merchant_id TEXT UNIQUE,
                user_id INTEGER REFERENCES budget_bot_users (user_id) ON DELETE RESTRICT,
                chat_id INTEGER,
                token TEXT, 
                bank TEXT,
                date_create TIMESTAMP,
                date_update TIMESTAMP,
                card_number TEXT,
                card_status SMALLINT,
                balance BIGINT,
                credit_limit BIGINT,
                currency_code SMALLINT,
                card_name TEXT,
                date_request TIMESTAMP,
                user_name TEXT);"""

        with DB() as db:
            db.execute(query)

    @staticmethod
    def is_user(user_id):
        with DB() as db:
            query = f"SELECT EXISTS(SELECT 1 FROM budget_bot_users WHERE user_id='%s');" % user_id
            db.execute(query)
            answer = db.fetchone()
            return answer[0]

    @staticmethod
    def add_user(message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        date_create = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        category = json.dumps(DB.category)
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        username = message.from_user.username
        language_code = message.from_user.language_code
        is_bot = message.from_user.is_bot

        values = f"{user_id}, {chat_id}, '{date_create}', '{category}', '{first_name}', '{last_name}', " \
                 f"'{username}', '{language_code}', {is_bot} "
        query = "INSERT INTO budget_bot_users (user_id, chat_id, date_create, category, first_name, last_name, " \
                "username, language_code, is_bot) " \
                "VALUES ({});".format(values)

        try:
            with DB() as db:
                db.execute(query)
                return True
        except Exception as e:
            message = 'Error add user in db.'
            if user_id:
                message += f'\nUser id: {user_id}'
            message += f'\n Error: {e}'
            logging.error(message)
            return False

    def add_data(self, message, description=None):
        message_id = message.message_id
        user_id = message.from_user.id
        chat_id = message.chat.id
        date_create = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text = message.reply_to_message.text
        category = text.split('.')[0].split(':')[1]
        if text.split('.')[1].rfind('Подкатегория') != -1:
            subcategory = text.split('.')[1].split(':')[1]
        else:
            subcategory = None

        amount = re.findall(r'\d+[.]\d+|\d+', message.text)[0]
        amount = round(float(amount), 2) * 100

        is_income = None
        for key, values in self.get_category(message.from_user.id).items():
            if values.get('name') == category.strip():
                is_income = values.get('is_income')

        if is_income is not None:
            self.update_balance(user_id, amount, is_income)

        balance = self.get_balance(message.from_user.id)

        values = f"{message_id}, {user_id}, {chat_id}, '{date_create}', '{category}', " \
                 f"{amount}, {is_income}, 1, '{message_id}', '{date_create}', 980, 'bot', {balance}"

        fields = "message_id, user_id, chat_id, date_create, category, amount, is_income, " \
                 "status, transaction_id, date_update, currency_code, type, balance"

        if subcategory:
            fields += ', subcategory'
            values += f", '{subcategory}'"

        if description:
            fields += ", description"
            values += f", '{description}'"

        query = "INSERT INTO budget_bot_data ({})" \
                " VALUES ({});".format(fields, values)

        try:
            with DB() as db:
                db.execute(query)
        except Exception as e:
            message = 'Error add data in db.'
            if user_id:
                message += f'\nUser id: {user_id}'
            message += f'\nError: {e}'
            logging.error(message)
            return False

        return balance

    @staticmethod
    def set_balance(user_id, amount):
        query = f"UPDATE budget_bot_users SET balance = {amount} WHERE user_id = {user_id};"

        with DB() as db:
            db.execute(query)
            return True

    @staticmethod
    def get_balance(user_id):
        query = f"SELECT balance FROM budget_bot_users WHERE user_id = {user_id};"
        with DB() as db:
            db.execute(query)
            answer = db.fetchone()
            return answer[0]

    @staticmethod
    def update_balance(user_id, amount, is_income):
        if is_income:
            query = f"UPDATE budget_bot_users SET balance = balance + {amount} WHERE user_id = {user_id};"
        else:
            query = f"UPDATE budget_bot_users SET balance = balance - {amount} WHERE user_id = {user_id};"

        with DB() as db:
            db.execute(query)
            return True

    @staticmethod
    def set_balance_transaction(id_, amount):
        query = f"UPDATE budget_bot_data SET balance = {amount} WHERE transaction_id = '{id_}';"

        with DB() as db:
            db.execute(query)
            return True

    @staticmethod
    def add_data_from_api(data):
        message_id = data['message_id']
        user_id = data['user_id']
        chat_id = data['chat_id']
        transaction_id = data['transaction_id']
        merchant_id = data['merchant_id']
        date_create = data['date_create']
        amount = data['amount']
        commission = data['commission']
        cashback = data['cashback']
        currency_code = data['currency_code']
        description = data['description']
        card_balance = data['card_balance']
        type_ = data['type']
        status = data['status']
        is_income = data['is_income']
        message_text = data['message_text']

        values = f"{message_id}, {user_id}, {chat_id}, '{transaction_id}', '{merchant_id}', '{date_create}', {amount}," \
                 f"{commission}, {cashback}, {currency_code}, '{description}', {card_balance}, '{type_}', {status}, {is_income}, '{message_text}'"

        query = "INSERT INTO budget_bot_data (message_id, user_id, chat_id, transaction_id, merchant_id, date_create, " \
                "amount, commission, cashback, currency_code, description, card_balance, type, status, is_income,  message_text)VALUES ({});".format(
            values)

        try:
            with DB() as db:
                db.execute(query)
                return transaction_id

        except Exception as e:
            message = 'Error add data from api in db.'
            if data.get('user_id'):
                message += f'\nUser id: {user_id}'
            message += f'\nError: {e}'
            logging.error(message)

    @staticmethod
    def get_new_transaction():
        with DB() as db:
            query = "SELECT id, user_id, chat_id, message_text " \
                    "FROM budget_bot_data " \
                    "WHERE status = 0"
            db.execute(query)
            answer = db.fetchone()
            if answer:
                query = "UPDATE budget_bot_data " \
                        "SET status = 3 " \
                        "WHERE id = %s" % answer[0]
                db.execute(query)
                return answer

    @staticmethod
    def set_transaction_status(id_, status):
        with DB() as db:
            query = "UPDATE budget_bot_data " \
                    "SET status = %s" \
                    "WHERE transaction_id = '%s';" % (status, id_)
            db.execute(query)

    @staticmethod
    def get_amount_transaction(id_):
        with DB() as db:
            query = f"SELECT amount, is_income FROM budget_bot_data WHERE transaction_id = '{id_}'"
            db.execute(query)
            answer = db.fetchone()
            return int(answer[0]) if answer[1] else int(answer[0]) * (-1)

    @staticmethod
    def set_category(id_, category):
        with DB() as db:
            query = "UPDATE budget_bot_data " \
                    "SET category = '%s'" \
                    "WHERE transaction_id = '%s';" % (category, id_)
            db.execute(query)

    @staticmethod
    def set_subcategory(id_, subcategory):
        with DB() as db:
            query = "UPDATE budget_bot_data " \
                    "SET subcategory = '%s'" \
                    "WHERE transaction_id = '%s';" % (subcategory, id_)
            db.execute(query)

    @staticmethod
    def update_data(data: dict):
        values = ""
        for key, value in data.items():
            if key in ['id', 'message_id']:
                user = f'{key} = {int(value)}'
            elif key in ['transaction_id', 'merchant_id', 'date_create', 'category', 'subcategory', 'description',
                         'type', 'message_text', ]:
                values += f"{key} = '{str(value)}', "
            else:
                values += f"{key} = {int(value)}, "

        query = f"UPDATE budget_bot_data SET {values[:-1]} WHERE {user};"

        try:
            with DB() as db:
                db.execute(query)
                return True

        except Exception as e:
            message = 'Error update data.'
            if data.get('user_id'):
                message += f'\nUser id: {user_id}'
            message += f'\n Error: {e}'
            logging.error(message)

    @staticmethod
    def get_data(user_id):
        with DB() as db:
            query = "SELECT message_id, date_create, category, subcategory, amount, description, is_income," \
                    "balance, card_balance " \
                    "FROM budget_bot_data " \
                    "WHERE user_id= %s AND is_add_in_sheet IS FALSE AND status = 1 " \
                    "ORDER by date_create" % user_id

            db.execute(query)
            answer = db.fetchall()
            if answer is None:
                logging.error('ANSWER ERROR. QUERY: {}'.format(query))
            return answer

    @staticmethod
    def set_data_added(user_id, message_id, sheet_id):
        try:
            date_create = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with DB() as db:
                query = "UPDATE budget_bot_data " \
                        "SET is_add_in_sheet = TRUE , add_in_sheet_id = '%s', date_add_in_sheet = '%s' " \
                        "WHERE message_id in (%s) AND user_id = %s;" % (
                            sheet_id, date_create, ', '.join(message_id), user_id)
                db.execute(query)
            return True
        except Exception as e:
            logging.error(f'Error: {e}')
            return False

    @staticmethod
    def get_category(user_id):
        with DB() as db:
            query = "SELECT category FROM budget_bot_users WHERE user_id = %s" % user_id
            db.execute(query)
            answer = db.fetchone()
            if answer is None:
                logging.error('ANSWER ERROR. QUERY: {}'.format(query))

        return answer[0] if answer else None

    @staticmethod
    def update_category(user_id, category):
        # Нужно обнавлять и дату
        with DB() as db:
            query = "UPDATE budget_bot_users SET category = '{}' WHERE user_id = {} ;".format(json.dumps(category),
                                                                                              user_id)
            db.execute(query)

    def can_add_category(self, user_id):
        category = self.get_category(user_id)
        return len(category) < self.max_number_categories

    def can_add_subcategory(self, call):
        category = self.get_category(call.message.chat.id)
        callback_data = json.loads(call.data)
        category = category.get(callback_data.get('cat'), {})
        subcategory = category.get('subcategories', {})
        return len(subcategory) < self.max_number_subcategories

    @staticmethod
    def get_data_report(time_from, time_to, user_id, is_income, type_data=''):
        text = ''
        query_end = f" FROM budget_bot_data WHERE date_create BETWEEN '{time_from}' AND '{time_to}'" \
                    f" AND user_id= {user_id} AND is_income = {is_income} AND status= 1 "

        with DB() as db:
            query = f"SELECT DISTINCT category, subcategory {query_end};"
            db.execute(query)
            data = db.fetchall()

            if not len(data):
                return False

            query = "SELECT SUM (amount)" + query_end + ";"
            db.execute(query)
            amount = db.fetchone()[0]
            if amount:
                amount = int(amount) / 100
            text += f'Всего{type_data}: {amount}грн \n\n'

            dict_data = {'without_subcategory': [], 'with_subcategory': {}}
            for category, subcategory in data:
                if subcategory == 'None' or subcategory is None:
                    dict_data['without_subcategory'].append(category)
                else:
                    if category in dict_data['with_subcategory']:
                        dict_data['with_subcategory'][category].append(subcategory)
                    else:
                        dict_data['with_subcategory'][category] = [subcategory]

            for category, subcategories in dict_data['with_subcategory'].items():

                query = "SELECT SUM (amount)" + query_end + f"AND category = '{category}'" + ";"
                db.execute(query)
                amount_category = db.fetchone()[0]
                if amount_category:
                    amount_category = int(amount_category) / 100
                text += f'        {category.strip()} всего: {amount_category} грн:\n'
                for subcategory in subcategories:
                    query = "SELECT SUM (amount)" + query_end + \
                            f"AND category = '{category}' AND subcategory = '{subcategory}'" + ";"
                    db.execute(query)
                    amount_subcategory = db.fetchone()[0]
                    if amount_subcategory:
                        amount_subcategory = int(amount_subcategory) / 100
                    text += f'                {subcategory} - {amount_subcategory} грн\n'
                text += '\n'

            for category in dict_data['without_subcategory']:
                query = "SELECT SUM (amount)" + query_end + f"AND category = '{category}'" + ";"
                db.execute(query)
                amount_category = db.fetchone()[0]
                if amount_category:
                    amount_category = int(amount_category) / 100
                text += f'        {category.strip()}: {amount_category} грн\n'
        return text

    def generate_report(self, time_from, time_to, user_id):
        """Gathering report message"""

        costs = self.get_data_report(time_from, time_to, user_id, 'false', ' расходов')
        income = self.get_data_report(time_from, time_to, user_id, 'true', ' доходов')

        if costs or income:
            message = ''
            if costs:
                message += costs + '\n'
            if income:
                message += income + '\n'
            message += 'Дата: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n'
            message += '-' * 38 + '\n'
            return message

    def get_report_month(self, user_id):
        """
            Preparation of month selection buttons for a report

            Returns:
                buttons (dict): Dictionary of buttons, where the key is the number of the month
                and the value is its name

        """

        with DB() as db:
            date_from = datetime.now() - timedelta(days=365)
            query = "SELECT DISTINCT EXTRACT(MONTH FROM date_create), EXTRACT(YEAR FROM date_create) " \
                    "FROM budget_bot_data  WHERE date_create > '%s' AND user_id= %s AND status= 1" \
                    "ORDER BY EXTRACT(MONTH FROM date_create), " \
                    "EXTRACT(YEAR FROM date_create);" % \
                    (date_from.strftime('%Y-%m-%d %H:%M:%S'), user_id)
            db.execute(query)
            answer = db.fetchall()
            calendar_dict = {}
            for month, year in answer:
                year = int(year)
                month = int(month)
                if year in calendar_dict:
                    calendar_dict[year].append(month)
                else:
                    calendar_dict[year] = [month]

            dict_return = {}

            for year, months in sorted(calendar_dict.items()):
                if len(calendar_dict) < 2:
                    for month in months:
                        dict_return.update(
                            {f'{str(month)}_{str(year)[-1]}': self.calendar_month.get(month, 'Month_error')})
                else:
                    for month in months:
                        dict_return.update(
                            {f'{str(month)}_{str(year)[-1]}': self.calendar_month.get(month,
                                                                                      'Month_error') + f' {year}'})

        return dict_return

    def delete_category(self, message, id_category):
        category = self.get_category(message.chat.id)
        try:
            category.pop(str(id_category))
            self.update_category(message.chat.id, category)
            return True
        except KeyError:
            return False

    def delete_subcategory(self, message, id_category, id_subcategory):
        category = self.get_category(message.from_user.id)
        try:
            category[str(id_category)]['subcategories'].pop(str(id_subcategory))
            self.update_category(message.from_user.id, category)
            return True
        except KeyError:
            return False

    def add_category(self, message):
        category = self.get_category(message.from_user.id)
        try:
            can_add_id = ({str(x) for x in range(1, self.max_number_categories + 1)}).difference(set(category.keys()))
            if can_add_id:
                is_income = 'Введите новое имя категории доходов:' == message.reply_to_message.text
                category.update(
                    {min(can_add_id): {'name': f'{message.text}', 'subcategories': {}, 'is_income': is_income}})
                self.update_category(message.from_user.id, category)
                return True
            else:
                return False
        except KeyError:
            return False

    def add_subcategory(self, message):
        category = self.get_category(message.from_user.id)
        try:
            category_name = message.reply_to_message.text.split('.')[0].split(':')[1].strip()
            for key, value in category.items():
                if value.get('name') == category_name:
                    can_add_subcategory = ({str(x) for x in range(1, self.max_number_subcategories + 1)}).difference(
                        set(value.get('subcategories').keys()))
                    if can_add_subcategory:
                        category[key]['subcategories'].update(
                            {f'{min(can_add_subcategory)}': {'name': f'{message.text}'}})
                        self.update_category(message.from_user.id, category)
                        return True
                    else:
                        return False
        except KeyError:
            return False

    @staticmethod
    def get_google_sheets_id(user_id):
        with DB() as db:
            query = "SELECT sheet_id FROM budget_bot_users WHERE user_id= %s" % user_id
            db.execute(query)
            answer = db.fetchone()
            if answer is None:
                logging.error('ANSWER ERROR. QUERY: {}'.format(query))
        return answer[0]

    @staticmethod
    def set_google_sheets_id(user_id, id_sheet):
        # обновлять дату
        if id_sheet.rfind('https://docs.google.com') != -1:
            id_sheet = re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', id_sheet)[0]

        if not id_sheet:
            return
        with DB() as db:
            query = "UPDATE budget_bot_users SET sheet_id = '{}' WHERE user_id = {};".format(id_sheet,
                                                                                             user_id)
            db.execute(query)

        return id_sheet

    @staticmethod
    def get_google_sheet_id_change(user_id):
        with DB() as db:
            query = "SELECT sheet_id_change FROM budget_bot_users WHERE user_id= %s" % user_id
            db.execute(query)
            answer = db.fetchone()
            if answer is None:
                logging.error('ANSWER ERROR. QUERY: {}'.format(query))
        return answer[0]

    @staticmethod
    def set_google_sheet_id_change(user_id, id_sheet):
        # обновлять дату
        if id_sheet.rfind('https://docs.google.com') != -1:
            id_sheet = re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', id_sheet)[0]
        if not id_sheet:
            return
        with DB() as db:
            query = "UPDATE budget_bot_users SET sheet_id_change = '{}' WHERE user_id = {};".format(id_sheet, user_id)
            db.execute(query)
        return id_sheet

    @staticmethod
    def reset_google_sheets_id(user_id):
        with DB() as db:
            query = "UPDATE budget_bot_users SET sheet_id = NULL WHERE user_id = %s;" % user_id
            db.execute(query)

    @staticmethod
    def reset_google_sheet_id_change(user_id):
        with DB() as db:
            query = "UPDATE budget_bot_users SET sheet_id_change = NULL WHERE user_id = {};".format(user_id)
            db.execute(query)

    @staticmethod
    def create_sheets_for():
        with DB() as db:
            query = "SELECT DISTINCT user_id FROM budget_bot_users WHERE sheet_id is NULL ;"
            db.execute(query)
            answer = db.fetchall()
        return [user_id[0] for user_id in answer]

    @staticmethod
    def change_sheet_id():
        with DB() as db:
            query = "SELECT DISTINCT user_id FROM budget_bot_users WHERE sheet_id_change is NOT NULL ;"
            db.execute(query)
            answer = db.fetchall()
        return [user_id[0] for user_id in answer]

    @staticmethod
    def add_data_in_sheet():
        with DB() as db:
            query = "SELECT DISTINCT data.user_id " \
                    "FROM budget_bot_data as data INNER JOIN budget_bot_users as users " \
                    "ON data.user_id = users.user_id " \
                    "WHERE data.is_add_in_sheet IS FALSE AND users.sheet_id IS NOT NULL AND data.status = 1;"

            db.execute(query)
            answer = db.fetchall()

        return [user_id[0] for user_id in answer]

    def get_id_transaction(self, user_id, date_start=None, date_end=None):
        with DB() as db:
            if date_start:
                ''
            query = "SELECT transaction_id " \
                    "FROM budget_bot_data " \
                    "WHERE user_id = %s;" % user_id
            db.execute(query)
            answer = db.fetchall()
        return [user_id[0] for user_id in answer]

    @staticmethod
    def simple_commands(user_id, command):
        queries = {'balance': f"SELECT balance/100 FROM budget_bot_users WHERE user_id = {user_id};",
                   'year_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                    f"extract(year from date_create) = extract(year from current_date) "
                                    f"AND is_income = false AND user_id = {user_id}",
                   'year_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                  f"extract(year from date_create) = extract(year from current_date) "
                                  f"AND is_income = true AND user_id = {user_id}",
                   'previous_year_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                             f"extract(year from date_create) = extract(year from current_date) -1"
                                             f"AND is_income = false AND user_id = {user_id}",
                   'previous_year_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                           f"extract(year from date_create) = extract(year from current_date) -1"
                                           f"AND is_income = true AND user_id = {user_id}",
                   'monthly_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                       f"extract(month from date_create) = extract(month from current_date) "
                                       f"AND is_income = false AND user_id = {user_id}",
                   'monthly_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                     f"extract(month from date_create) = extract(month from current_date) "
                                     f"AND is_income = true AND user_id = {user_id}",
                   'previous_monthly_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                                f"extract(month from date_create) = extract(month from current_date) -1"
                                                f"AND is_income = false AND user_id = {user_id}",
                   'previous_monthly_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                              f"extract(month from date_create) = extract(month from current_date) -1"
                                              f"AND is_income = true AND user_id = {user_id}",
                   'week_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                    f"extract(week from date_create) = extract(week from current_date) "
                                    f"AND is_income = false AND user_id = {user_id}",
                   'week_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                  f"extract(month from date_create) = extract(month from current_date) "
                                  f"AND is_income = true AND user_id = {user_id}",
                   'previous_week_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                             f"extract(week from date_create) = extract(week from current_date) -1"
                                             f"AND is_income = false AND user_id = {user_id}",
                   'previous_week_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                           f"extract(month from date_create) = extract(month from current_date) -1"
                                           f"AND is_income = true AND user_id = {user_id}"
                   }
        query = queries.get(command)
        if query:
            with DB() as db:
                db.execute(query)
                return db.fetchone()[0]


if __name__ == '__main__':
    db_ = DB()
    # from budget_bot import BudgetBot
    # db_.add_user_()

    # b = BudgetBot()
    # print(db_.get_data(529088251))
    # print(db_.get_category(529088251))
    # print(db_.is_user(529088251))
    # db.get_report_month(529088251)
    # print(db.create_sheets_id())
    # print(db.change_sheet_id())
    # print(db_.add_data_in_sheet())
    # print(db_.get_balance(529088251))
    print(db_.set_balance_transaction('tXc2UvNSeN7GLKQ', 1000))
    # db.get_report_for_day(529088251)
    # print()
    # db.get_report_for_week(529088251)
    # print()
    # db.get_report_for_month(529088251)
    # db._create_table_users()
    # from time import sleep
    #
    # while True:
    #     data = db_.get_new_transaction()
    #     if data:
    #         b.add_from_api(id=data[0], user_id=data[1], chat_id=data[2], message_text=data[3])
    #     sleep(0.2)
    # db_._create_table_data()
    # db.reset_google_sheets_id(529088251)
    # db_._create_table_users()
    # db_._create_table_cards()
    # db_._create_table_data()
    # db_._create_table_users()

    # print('MonobankCумма: -165.00 грн.\nОписание: АТБ\nКашбек: 1.65грн\nБаланс: 4425.13\nВыбери категорию:'.encode('utf-8'))
