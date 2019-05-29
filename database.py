from setting import *
import re
import json
import psycopg2
import logging
from datetime import datetime


class DB:
    def __init__(self):
        self.category = {
            1: {'name': 'Питание',
                'subcategories': {1: {'name': 'Продукты'}, 2: {'name': 'Сладкое'}, 3: {'name': 'Прочее'}}},
            2: {'name': 'Заведения',
                'subcategories': {1: {'name': 'Кафе и рестораны'}, 2: {'name': 'Суши'}, 3: {'name': "McDonalds"},
                                  4: {'name': 'Прочее'}}},
            3: {'name': 'Квартира',
                'subcategories': {1: {'name': 'Аренда'}, 2: {'name': 'Комуналка'}, 3: {'name': 'Прочее'}}},
            4: {'name': 'Транспорт',
                'subcategories': {1: {'name': 'Маршрутка'}, 2: {'name': 'Метро'}, 3: {'name': 'Такси'}}},
            5: {'name': 'Здоровье',
                'subcategories': {1: {'name': 'Кафе и рестораны'}, 2: {'name': 'Суши'}, 3: {'name': "McDonalds"},
                                  4: {'name': 'Прочее'}}},
            6: {'name': 'Одежда',
                'subcategories': {1: {'name': 'Одежда'}, 2: {'name': 'Обувь'}, 3: {'name': 'Уход за одеждой'},
                                  4: {'name': 'Прочее'}}},
            7: {'name': 'Гигиена', 'subcategories': {}, },
            8: {'name': 'Отдых', 'subcategories': {}, },
            9: {'name': 'Спортзал', 'subcategories': {}, },
            10: {'name': 'Здоровье', 'subcategories': {}, },
            11: {'name': 'Техника', 'subcategories': {}, },
            12: {'name': 'Связь', 'subcategories': {}, },
        }
        self.finance_category = {1: {'name': 'Зарплата'}, 2: {'name': 'Пасиыв'}, 3: {'name': 'Прочее'}}
        try:
            self.connection = psycopg2.connect(database=database,
                                               host=db_host,
                                               user=db_user,
                                               password=db_password,
                                               port='5432')
            print(self.connection)
        except Exception as e:
            logging.error(e)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()

    def commit(self):
        self.connection.commit()

    def add_user(self, message):

        user_id = message.from_user.id
        chat_id = message.chat.id
        date_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet_id = '1i3GPjDataKVzFZLXBs0WdmD9kISIivBAl--8C1KkX3g'
        category = json.dumps(self.category)
        finance_category = json.dumps(self.finance_category)
        balance = 0
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        username = message.from_user.username
        language_code = message.from_user.language_code
        is_bot = message.from_user.is_bot
        data_sheet_id = 1215147421
        values = f"{user_id}, {chat_id}, '{date_update}', '{sheet_id}', '{category}', '{finance_category}', " \
                 f"{balance}, '{first_name}', '{last_name}', '{username}', '{language_code}', {is_bot}, {data_sheet_id}"
        query = "INSERT INTO budget_bot_users (user_id,chat_id, date_update, sheet_id, category, finance_category," \
                " balance, first_name, last_name, username, language_code, is_bot, data_sheet_id) VALUES ({});".format(
            values)

        try:
            with DB() as db:
                cursor = db.cursor()
                cursor.execute(query)
                db.commit()
        except psycopg2.errors.UniqueViolation as e:
            print(e)

    def get_category(self, user_id):
        with DB() as db:
            cursor = db.cursor()
            query = "SELECT category FROM budget_bot_users WHERE user_id= %s" % user_id
            cursor.execute(query)
            answer = cursor.fetchone()
            if answer is None:
                logging.error('ANSWER ERROR. QUERY: {}'.format(query))
                answer = [{}]
        return answer[0]

    def update_category(self, user_id, category):
        print('update_category')
        print(category)
        with DB() as db:
            cursor = db.cursor()
            query = "UPDATE budget_bot_users SET category = '{}' WHERE user_id = {} ;".format(json.dumps(category), user_id)
            print(query)
            cursor.execute(query)
            db.commit()

    def can_add_category(self, message):
        return True
        from random import randint
        return randint(0, 1)

    def can_add_subcategory(self, message):
        return True
        from random import randint
        return randint(0, 1)

    def get_report_month(self, message):
        return {1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май'}

    def get_report_day(self, message):
        return {x: x for x in range(1, 32)}

    def delete_category(self, message, id_category):
        print('delete_category')
        print(message)
        category = self.get_category(message.chat.id)
        print(id_category)
        print(category)
        try:
            category.pop(str(id_category))
            self.update_category(message.chat.id, category)
            return True
        except KeyError:
            return False

    def delete_subcategory(self, message, id_category, id_subcategory):
        print('delete_subcategory')
        category = self.get_category(message.from_user.id)
        print(id_category)
        print(id_subcategory)
        print(category)
        try:
            category[str(id_category)]['subcategories'].pop(str(id_subcategory))
            self.update_category(message.from_user.id, category)
            return True
        except KeyError:
            return False

    def add_category(self, message):
        print('add_category')
        category = self.get_category(message.from_user.id)
        print(category)

        try:
            can_add_id = ({str(x) for x in range(1, 16)}).difference(set(category.keys()))
            if can_add_id:
                category.update({min(can_add_id): {'name': f'{message.text}', 'subcategories': {}, }})
                self.update_category(message.from_user.id, category)
                return True
            else:
                return False
        except KeyError:
            return False

    def add_subcategory(self, message):
        print('add_subcategory')
        print(message)
        category = self.get_category(message.from_user.id)
        print(category)

        try:
            category_name = message.reply_to_message.text.split('.')[0].split(':')[1].strip()
            for key, value in category.items():
                if value.get('name') == category_name:
                    print(value)
                    print(value.get('subcategories'))
                    can_add_subcat = ({str(x) for x in range(1, 7)}).difference(set(value.get('subcategories').keys()))
                    print(can_add_subcat)
                    print(min(can_add_subcat))
                    if can_add_subcat:
                        category[key]['subcategories'].update({f'{min(can_add_subcat)}': {'name': f'{message.text}'}})
                        self.update_category(message.from_user.id, category)
                        return True
                    else:
                        return False
        except KeyError:
            return False

    def get_google_sheets_id(self, message):
        return '1i3GPjDataKVzFZLXBs0WdmD9kISIivBAl--8C1KkX3g'

    def set_google_sheets_id(self, message):
        id_sheets = (re.findall(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', message.text))
        if True:  # попытка подконектиться
            return id_sheets
