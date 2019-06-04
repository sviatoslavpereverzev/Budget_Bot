from setting import *
import re
import json
import psycopg2
import logging
from datetime import datetime, timedelta

MAXIMUM_NUMBER_CATEGORIES = 15
MAXIMUM_NUMBER_SUBCATEGORIES = 6


class DB:
    def __init__(self):
        self.category = {
            1: {'name': 'Питание',
                'subcategories': {1: {'name': 'Продукты'}, 2: {'name': 'Сладкое'}, 3: {'name': 'Прочее'}, },
                'is_income': False},
            2: {'name': 'Заведения',
                'subcategories': {1: {'name': 'Кафе и рестораны'}, 2: {'name': 'Суши'}, 3: {'name': "McDonalds"},
                                  4: {'name': 'Прочее'}}, 'is_income': False},
            3: {'name': 'Квартира',
                'subcategories': {1: {'name': 'Аренда'}, 2: {'name': 'Комуналка'}, 3: {'name': 'Прочее'}},
                'is_income': False},
            4: {'name': 'Транспорт',
                'subcategories': {1: {'name': 'Маршрутка'}, 2: {'name': 'Метро'}, 3: {'name': 'Такси'}},
                'is_income': False},
            5: {'name': 'Здоровье',
                'subcategories': {1: {'name': 'Кафе и рестораны'}, 2: {'name': 'Суши'}, 3: {'name': "McDonalds"},
                                  4: {'name': 'Прочее'}}, 'is_income': False},
            6: {'name': 'Одежда',
                'subcategories': {1: {'name': 'Одежда'}, 2: {'name': 'Обувь'}, 3: {'name': 'Уход за одеждой'},
                                  4: {'name': 'Прочее'}}, 'is_income': False},
            7: {'name': 'Гигиена', 'subcategories': {}, 'is_income': False},
            8: {'name': 'Отдых', 'subcategories': {}, 'is_income': False},
            9: {'name': 'Спортзал', 'subcategories': {}, 'is_income': False},
            10: {'name': 'Здоровье', 'subcategories': {}, 'is_income': False},
            11: {'name': 'Техника', 'subcategories': {}, 'is_income': False},
            12: {'name': 'Доходы', 'subcategories': {}, 'is_income': True},
        }
        self.finance_category = {1: {'name': 'Зарплата'}, 2: {'name': 'Пасиыв'}, 3: {'name': 'Прочее'}}
        try:
            self.connection = psycopg2.connect(database=database,
                                               host=db_host,
                                               user=db_user,
                                               password=db_password,
                                               port='5432')
            self.connection.autocommit = True
        except Exception as e:
            logging.error(e)

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
        date_update TIMESTAMP,
        sheet_id TEXT,
        category JSON,
        balance MONEY DEFAULT 0,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        language_code TEXT,
        is_bot BOOL,
        data_sheet_id TEXT);"""

        with DB() as db:
            db.execute(query)

    @staticmethod
    def _create_table_data():
        query = """
            CREATE TABLE budget_bot_data (
            message_id INTEGER PRIMARY KEY ,
            user_id INTEGER REFERENCES budget_bot_users (user_id) ON DELETE RESTRICT,
            chat_id INTEGER,
            date_add TIMESTAMP,
            category TEXT,
            subcategory TEXT,
            amount MONEY,
            is_income BOOL,
            is_add_in_sheet BOOL DEFAULT FALSE,
            add_in_sheet_id TEXT,
            date_add_in_sheet TIMESTAMP);"""

        with DB() as db:
            db.execute(query)

    def add_user(self, message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        date_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        category = json.dumps(self.category)
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        username = message.from_user.username
        language_code = message.from_user.language_code
        is_bot = message.from_user.is_bot
        values = f"{user_id}, {chat_id}, '{date_update}', '{category}', '{first_name}', '{last_name}', " \
                 f"'{username}', '{language_code}', {is_bot} "
        query = "INSERT INTO budget_bot_users (user_id, chat_id, date_update, category, first_name, last_name, " \
                "username, language_code, is_bot) " \
                "VALUES ({});".format(values)

        try:
            with DB() as db:
                db.execute(query)
        except psycopg2.errors.UniqueViolation as e:
            print(e)
        else:
            # google_sheets_api.create_table()
            return True

    def add_data(self, message):
        print('add_data')

        message_id = message.message_id
        user_id = message.from_user.id
        chat_id = message.chat.id
        date_add = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text = message.reply_to_message.text
        category = text.split('.')[0].split(':')[1]
        if text.split('.')[1].rfind('Подкатегория') != -1:
            subcategory = text.split('.')[1].split(':')[1]
        else:
            subcategory = None
        amount = round(float(message.text), 2)
        for key, values in self.get_category(message.from_user.id).items():
            if values.get('name') == category.strip():
                is_income = values.get('is_income')

        values = f"{message_id}, {user_id}, {chat_id}, '{date_add}', '{category}', '{subcategory}',  {amount}, {is_income}"
        query = "INSERT INTO budget_bot_data (message_id, user_id, chat_id, date_add, category, subcategory, amount, is_income)" \
                " VALUES ({});".format(values)

        try:
            with DB() as db:
                db.execute(query)
                return True
        except psycopg2.errors.UniqueViolation as e:
            print(e)

    @staticmethod
    def get_category(user_id):
        with DB() as db:
            query = "SELECT category FROM budget_bot_users WHERE user_id= %s" % user_id
            db.execute(query)
            answer = db.fetchone()
            if answer is None:
                logging.error('ANSWER ERROR. QUERY: {}'.format(query))

        return answer[0] if answer else None

    @staticmethod
    def update_category(user_id, category):
        print('update_category')

        # Нужно обнавлять и дату
        with DB() as db:
            query = "UPDATE budget_bot_users SET category = '{}' WHERE user_id = {} ;".format(json.dumps(category),
                                                                                              user_id)
            db.execute(query)

    def can_add_category(self, user_id):
        category = self.get_category(user_id)
        return len(category) < MAXIMUM_NUMBER_CATEGORIES

    def can_add_subcategory(self, call):
        print('can_add_subcategory')

        category = self.get_category(call.message.chat.id)
        callback_data = json.loads(call.data)
        category = category.get(callback_data.get('cat'), {})
        subcategory = category.get('subcategories')
        return len(subcategory) < MAXIMUM_NUMBER_SUBCATEGORIES

    @staticmethod
    def get_data_report(time_from, time_to, user_id, is_income, type_data=''):
        text = ''
        query_end = f" FROM budget_bot_data WHERE date_add BETWEEN '{time_from}' AND '{time_to}'" \
                    f" AND user_id= {user_id} AND is_income = {is_income} "

        with DB() as db:
            query = "SELECT DISTINCT category, subcategory" + query_end + ";"
            db.execute(query)
            data = db.fetchall()

            if not len(data):
                return False

            query = "SELECT SUM (amount::money::numeric::float8)" + query_end + ";"
            db.execute(query)
            amount = db.fetchone()[0]
            if amount.is_integer():
                amount = int(amount)
            text += f'Всего{type_data}: {amount}грн \n\n'

            dict_data = {'without_subcategory': [], 'with_subcategory': {}}
            for category, subcategory in data:
                if subcategory == 'None':
                    dict_data['without_subcategory'].append(category)
                else:
                    if category in dict_data['with_subcategory']:

                        dict_data['with_subcategory'][category].append(subcategory)
                    else:
                        dict_data['with_subcategory'][category] = [subcategory]

            for category, subcategories in dict_data['with_subcategory'].items():

                query = "SELECT SUM (amount::money::numeric::float8)" + query_end + f"AND category = '{category}'" + ";"
                db.execute(query)
                amount_category = db.fetchone()[0]
                if amount_category.is_integer():
                    amount_category = int(amount_category)
                text += f'        {category.strip()} всего: {amount_category} грн:\n'
                for subcategory in subcategories:
                    query = "SELECT SUM (amount::money::numeric::float8)" + query_end + \
                            f"AND category = '{category}' AND subcategory = '{subcategory}'" + ";"
                    db.execute(query)
                    amount_subcategory = db.fetchone()[0]
                    if amount_subcategory.is_integer():
                        amount_subcategory = int(amount_subcategory)
                    text += f'                {subcategory} - {amount_subcategory} грн\n'
                text += '\n'

            for category in dict_data['without_subcategory']:
                query = "SELECT SUM (amount::money::numeric::float8)" + query_end + f"AND category = '{category}'" + ";"
                db.execute(query)
                amount_category = db.fetchone()[0]
                if amount_category.is_integer():
                    amount_category = int(amount_category)
                text += f'        {category.strip()}: {amount_category} грн\n'
        return text

    def generate_report(self, time_from, time_to, user_id):
        costs = self.get_data_report(time_from, time_to, user_id, 'false', ' расходов')
        income = self.get_data_report(time_from, time_to, user_id, 'true', ' доходов')

        if costs or income:
            message = ''
            if costs:
                message += costs + '\n'
            if income:
                message += income + '\n'
            message += 'Дата: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n'
            message += '-' * 50 + '\n'
            return message

    def get_report_month(self, user_id):
        calendar_month = {
            1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Августу',
            9: 'Сентабрь',
            10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
        }
        with DB() as db:
            date_from = datetime.now() - timedelta(days=365)
            query = """
                SELECT DISTINCT EXTRACT(MONTH FROM date_add), EXTRACT(YEAR FROM date_add)
                FROM budget_bot_data 
                WHERE date_add > '%s' AND user_id= %s
                ORDER BY EXTRACT(MONTH FROM date_add),   EXTRACT(YEAR FROM date_add);""" % \
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
                        dict_return.update({f'{str(month)}_{str(year)[-1]}': calendar_month.get(month, 'Month_error')})
                else:
                    for month in months:
                        dict_return.update(
                            {f'{str(month)}_{str(year)[-1]}': calendar_month.get(month, 'Month_error') + f' {year}'})

        return dict_return

    def delete_category(self, message, id_category):
        print('delete_category')

        category = self.get_category(message.chat.id)
        try:
            category.pop(str(id_category))
            self.update_category(message.chat.id, category)
            return True
        except KeyError:
            return False

    def delete_subcategory(self, message, id_category, id_subcategory):
        print('delete_subcategory')

        category = self.get_category(message.from_user.id)
        try:
            category[str(id_category)]['subcategories'].pop(str(id_subcategory))
            self.update_category(message.from_user.id, category)
            return True
        except KeyError:
            return False

    def add_category(self, message):
        print('add_category')

        category = self.get_category(message.from_user.id)
        try:
            can_add_id = ({str(x) for x in range(1, MAXIMUM_NUMBER_CATEGORIES + 1)}).difference(set(category.keys()))
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
        print('add_subcategory')

        category = self.get_category(message.from_user.id)
        try:
            category_name = message.reply_to_message.text.split('.')[0].split(':')[1].strip()
            for key, value in category.items():
                if value.get('name') == category_name:
                    can_add_subcategory = ({str(x) for x in range(1, MAXIMUM_NUMBER_SUBCATEGORIES + 1)}).difference(
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

    def set_google_sheets_id(self, message):
        print('set_google_sheets_id')

        # обновлять дату
        id_sheets = (re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', message.text))
        if id_sheets:
            if True:  # попытка подконектиться
                pass

            with DB() as db:
                query = "UPDATE budget_bot_users SET sheet_id = '{}' WHERE user_id = {};".format(id_sheets[0],
                                                                                                 message.from_user.id)
                db.execute(query)
                query = "SELECT sheet_id FROM budget_bot_users WHERE user_id= %s" % message.from_user.id
                db.execute(query)
                answer = db.fetchone()
                if answer is None:
                    logging.error('ANSWER ERROR. QUERY: {}'.format(query))

            return answer[0]


if __name__ == '__main__':
    db = DB()
    db.get_report_month(529088251)
    # db.get_report_for_day(529088251)
    # print()
    # db.get_report_for_week(529088251)
    # print()
    # db.get_report_for_month(529088251)
    # db._create_table_users()
    # db._create_table_data()
