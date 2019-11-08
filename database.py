# -*- coding: utf-8 -*-
import os
import re
import json
import logging
from configparser import ConfigParser
from datetime import datetime, timedelta

from sqlalchemy import create_engine, distinct
from sqlalchemy.orm import sessionmaker

from models.users import Users
from models.users import Data


# дописать комментарии
# удалить лишнее
# обновлять дату при запросах:


class DB:
    """Class to work with Budget Bot database"""

    def __init__(self):

        self.session = None
        self.engine = None
        self.db_url = None

        # maximum number of categories
        self.max_number_categories = None
        # maximum number of subcategories
        self.max_number_subcategories = None

        self.set_settings()

    def set_settings(self):
        config = ConfigParser()
        config.read(os.path.dirname(os.path.abspath(__file__)) + '/config/app.ini')
        self.db_url = config.get('DATABASE', 'url')
        self.max_number_categories = config.getint('BUDGET_BOT', 'max_number_categories')
        self.max_number_subcategories = config.getint('BUDGET_BOT', 'max_number_subcategories')
        self.connect_db()

    def connect_db(self):
        db_engine = create_engine(self.db_url)
        db_session = sessionmaker()
        db_session.configure(bind=db_engine)
        self.session = db_session()
        self.engine = db_engine

    def is_user(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        return True if user else False

    def add_user(self, message):
        user = Users(user_id=message.from_user.id,
                     chat_id=message.chat.id,
                     date_create=datetime.now(),
                     date_update=datetime.now(),
                     first_name=message.from_user.first_name,
                     last_name=message.from_user.last_name,
                     username=message.from_user.username,
                     language_code=message.from_user.language_code,
                     is_bot=message.from_user.is_bot)

        self.session.add(user)

        try:
            self.session.commit()
            return True
        except Exception as e:
            logging.error(f'Error add user in db.\nUser id: {message.from_user.id}\n Error: {e}')
            return False

    def add_data(self, message, description=None):
        text = message.reply_to_message.text
        category = text.split('.')[0].split(':')[1].strip()
        if text.split('.')[1].rfind('Подкатегория') != -1:
            subcategory = text.split('.')[1].split(':')[1].strip()
        else:
            subcategory = None

        amount = re.findall(r'\d+[.]\d+|\d+', message.text)[0]
        amount = round(float(amount), 2) * 100

        is_income = None
        for key, values in self.get_category(message.from_user.id).items():
            if values.get('name') == category.strip():
                is_income = values.get('is_income')

        if is_income is not None:
            self.update_balance(message.from_user.id, amount, is_income)

        balance = self.get_balance(message.from_user.id)

        data = Data(message_id=message.message_id,
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    transaction_id=message.message_id,
                    date_create=datetime.now(),
                    date_update=datetime.now(),
                    category=category,
                    subcategory=subcategory,
                    amount=amount,
                    currency_code=980,
                    is_income=is_income,
                    status=1,
                    type='bot',
                    balance=balance,
                    description=description)

        self.session.add(data)

        try:
            self.session.commit()
        except Exception as e:
            message = f'Error add data in db.\nUser id: {message.from_user.id}.\nError: {e}'
            return False

        return balance

    def set_balance(self, user_id, amount):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        user.balance = amount
        self.session.commit()
        return True

    def get_balance(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        return user.balance

    def update_balance(self, user_id, amount, is_income):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        if is_income:
            user.balance = user.balance + amount
        else:
            user.balance = user.balance - amount
        self.session.commit()
        return True

    def set_balance_transaction(self, transaction_id, amount):
        transaction = self.session.query(Data).filter(Data.transaction_id == transaction_id).first()
        if transaction:
            transaction.balance = amount
            self.session.commit()
            return True

    def add_data_from_api(self, api_data):
        data = Data(message_id=api_data['message_id'],
                    user_id=api_data['user_id'],
                    chat_id=api_data['chat_id'],
                    transaction_id=api_data['transaction_id'],
                    merchant_id=api_data['merchant_id'],
                    date_create=api_data['date_create'],
                    amount=api_data['amount'],
                    commission=api_data['commission'],
                    cashback=api_data['cashback'],
                    currency_code=api_data['currency_code'],
                    description=api_data['description'],
                    card_balance=api_data['card_balance'],
                    type=api_data['type'],
                    status=api_data['status'],
                    is_income=api_data['is_income'], )
        self.session.add(data)

        try:
            self.session.commit()
            return api_data['transaction_id']

        except Exception as e:
            logging.error(f'Error add data from api in db.\nUser id: {api_data["user_id"]}.\nError: {e}')

    def set_transaction_status(self, transaction_id, status):
        transaction = self.session.query(Data).filter(Data.transaction_id == transaction_id).first()
        transaction.status = status
        self.session.commit()

    def get_amount_transaction(self, transaction_id):
        transaction = self.session.query(Data).filter(Data.transaction_id == transaction_id).first()
        if transaction:
            return transaction.amount if transaction.is_income else transaction.amount * -1

    def set_category(self, transaction_id, category):
        transaction = self.session.query(Data).filter(Data.transaction_id == transaction_id).first()
        transaction.category = category
        self.session.commit()

    def set_subcategory(self, transaction_id, subcategory):
        transaction = self.session.query(Data).filter(Data.transaction_id == transaction_id).first()
        transaction.subcategory = subcategory
        self.session.commit()

    def get_data(self, user_id):
        transactions = self.session.query(Data).filter(Data.user_id == user_id,
                                                       Data.is_add_in_sheet == False,
                                                       Data.status == 1).order_by(Data.date_create).all()
        data = []
        if transactions:
            for transaction in transactions:
                data.append(
                    (transaction.message_id, transaction.date_create, transaction.category, transaction.subcategory,
                     transaction.amount, transaction.description, transaction.is_income, transaction.balance,
                     transaction.card_balance))
            return data

    def set_data_added(self, user_id, messages_id, sheet_id):
        transactions = self.session.query(Data).filter(Data.user_id == user_id, Data.message_id.in_(messages_id)).all()
        for transaction in transactions:
            transaction.date_update = datetime.now()
            transaction.is_add_in_sheet = True
            transaction.add_in_sheet_id = sheet_id
            transaction.date_add_in_sheet = datetime.now()

        try:
            self.session.commit()
            return True
        except Exception as e:
            logging.error(f'Error: {e}')
            return False

    def get_category(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        return user.category if user else None

    def update_category(self, user_id, category):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        user.date_update = datetime.now()
        user.category = category
        self.session.commit()

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
                    {min(can_add_id): {'name': f'{message.text.strip()}', 'subcategories': {}, 'is_income': is_income}})
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
                            {f'{min(can_add_subcategory)}': {'name': f'{message.text.strip()}'}})
                        self.update_category(message.from_user.id, category)
                        return True
                    else:
                        return False
        except KeyError:
            return False

    def get_google_sheets_id(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        return user.sheet_id

    def set_google_sheets_id(self, user_id, sheet_id):
        if sheet_id.rfind('https://docs.google.com') != -1:
            sheet_id = re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_id)[0]

        if not sheet_id:
            return

        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        user.date_update = datetime.now()
        user.sheet_id = sheet_id
        self.session.commit()
        return sheet_id

    def get_google_sheet_id_change(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        return user.sheet_id_change

    def set_google_sheet_id_change(self, user_id, sheet_id):
        if sheet_id.rfind('https://docs.google.com') != -1:
            sheet_id = re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_id)[0]
        if not sheet_id:
            return

        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        user.date_update = datetime.now()
        user.sheet_id_change = sheet_id
        self.session.commit()
        return sheet_id

    def reset_google_sheets_id(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        user.date_update = datetime.now()
        user.sheet_id = None
        self.session.commit()

    def reset_google_sheet_id_change(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        user.date_update = datetime.now()
        user.sheet_id_change = None
        self.session.commit()

    def create_sheets_for(self):
        users = self.session.query(Users).filter(Users.sheet_id == None).all()
        return [user.user_id for user in users] if users else []

    def change_sheet_id(self):
        users = self.session.query(Users).filter(Users.sheet_id_change != None).all()
        return [user.user_id for user in users] if users else []

    def add_data_in_sheet(self):
        transactions = self.session.query(Data, Users) \
            .join(Users, Users.user_id == Data.user_id) \
            .filter(Data.is_add_in_sheet == False,
                    Users.sheet_id != None,
                    Data.status == 1).distinct(Users.user_id).all()
        return [transaction.user_id for transaction, user in transactions] if transactions else []

    @staticmethod
    def simple_commands(user_id, command):
        queries = {'balance': f"SELECT balance/100 FROM budget_bot_users WHERE user_id = {user_id};",
                   'earnings_per_hour': f"SELECT div(SUM(amount/100), 720) FROM budget_bot_data WHERE status = 1 and "
                                        f"date_create > current_date - 30 AND is_income = true AND user_id = {user_id}",
                   'cost_per_hour': f"SELECT div(SUM(amount/100), 720) FROM budget_bot_data WHERE status = 1 and "
                                    f"date_create > current_date - 30 AND is_income = false AND user_id = {user_id}",
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
                                       f"AND extract(year from date_create) = extract(year from current_date)"
                                       f"AND is_income = false AND user_id = {user_id}",
                   'monthly_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                     f"extract(month from date_create) = extract(month from current_date) "
                                     f"AND extract(year from date_create) = extract(year from current_date)"
                                     f"AND is_income = true AND user_id = {user_id}",
                   'previous_monthly_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                                f"extract(month from date_create) = extract(month from current_date) -1"
                                                f" AND extract(year from date_create) = extract(year from current_date)"
                                                f"AND is_income = false AND user_id = {user_id}",
                   'previous_monthly_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                              f"extract(month from date_create) = extract(month from current_date) -1 "
                                              f"AND extract(year from date_create) = extract(year from current_date)"
                                              f"AND is_income = true AND user_id = {user_id}",
                   'week_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                    f"extract(week from date_create) = extract(week from current_date) "
                                    f"AND extract(year from date_create) = extract(year from current_date)"
                                    f"AND is_income = false AND user_id = {user_id}",
                   'week_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                  f"extract(month from date_create) = extract(month from current_date) "
                                  f"AND extract(year from date_create) = extract(year from current_date)"
                                  f"AND is_income = true AND user_id = {user_id}",
                   'previous_week_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                             f"extract(week from date_create) = extract(week from current_date) -1 "
                                             f"AND extract(year from date_create) = extract(year from current_date)"
                                             f"AND is_income = false AND user_id = {user_id}",
                   'previous_week_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                           f"extract(month from date_create) = extract(month from current_date) -1 "
                                           f"AND extract(year from date_create) = extract(year from current_date)"
                                           f"AND is_income = true AND user_id = {user_id}",
                   'day_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                   f"extract(day from date_create) = extract(day from current_date) "
                                   f"AND extract(year from date_create) = extract(year from current_date)"
                                   f"AND extract(month from date_create) = extract(month from current_date)"
                                   f"AND is_income = false AND user_id = {user_id}",
                   'day_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                 f"extract(day from date_create) = extract(day from current_date) "
                                 f"AND extract(year from date_create) = extract(year from current_date)"
                                 f"AND extract(month from date_create) = extract(month from current_date)"
                                 f"AND is_income = true AND user_id = {user_id}",
                   'previous_day_expenses': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                            f"extract(day from date_create) = extract(day from current_date) -1 "
                                            f"AND extract(year from date_create) = extract(year from current_date)"
                                            f"AND extract(month from date_create) = extract(month from current_date)"
                                            f"AND is_income = false AND user_id = {user_id}",
                   'previous_day_income': f"SELECT SUM (amount/100) FROM budget_bot_data WHERE status = 1 and "
                                          f"extract(day from date_create) = extract(day from current_date) -1 "
                                          f"AND extract(year from date_create) = extract(year from current_date)"
                                          f"AND extract(month from date_create) = extract(month from current_date)"
                                          f"AND is_income = true AND user_id = {user_id}"
                   }

        for key in queries:
            print(key)
        query = queries.get(command)
        if query:
            with DB() as db:
                db.execute(query)
                return db.fetchone()[0]

    def can_work_in_group(self, user_id):
        user = self.session.query(Users).filter(Users.user_id == user_id).first()
        return user.groups_allowed if user else False


if __name__ == '__main__':
    db = DB()
    # print(db.is_user(529088251))
    # print(db.add_user(''))
    # print(db.get_amount_transaction('154'))
    # db.set_subcategory('154', 'Test')
    # db.set_transaction_status('154', 1)
    # db.set_balance(529088251, 100500)
    # print(db.get_balance(529088251))
    # db.update_balance(529088251, 1000, False)
    # db.set_balance_transaction('154', 100)
    # print(db.get_category(529088251))

    # print(sorted(db.get_data(529088251)))
    # db.set_data_added(529088251, [167, 163, 172, 154], 'test')
    # db.update_category(529088251, {})
    # print(db.can_add_category(529088251))
    # print(db.set_google_sheet_id_change(529088251, 'test'))
    # print(db.reset_google_sheet_id_change(529088251, ))
    # print(db.create_sheets_for())
    # print(db.change_sheet_id())
    # print(db.add_data_in_sheet())
    # print(db.can_work_in_group(529088251))
