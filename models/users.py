# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, BigInteger, Date, Numeric, Boolean, String, DECIMAL, JSON, DateTime, ForeignKey, \
    SmallInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Users(Base):
    # category is a dictionary which contains all basic categories and subcategories
    # the key is the category id
    # id/name this category name
    # id/is_income shows whether this category is income if not then it is an expense
    # id/subcategories this is a dictionary of subcategories in which the key is a category id
    # id/subcategories/name subcategory name
    CATEGORY = {
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

    __tablename__ = 'budget_bot_users'

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(Integer)
    date_create = Column(DateTime)
    date_update = Column(DateTime)
    sheet_id = Column(String)
    category = Column(JSON, default=CATEGORY)
    balance = Column(Integer, default=0)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String)
    language_code = Column(String)
    is_bot = Column(Boolean)
    data_sheet_id = Column(String)
    sheet_id_change = Column(String)
    groups_allowed = Column(Boolean, default=False)


class Data(Base):
    __tablename__ = 'budget_bot_data'

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer)
    user_id = Column(Integer, ForeignKey('budget_bot_users.user_id', ondelete='RESTRICT'))
    user = relationship("Users", backref='budget_bot_data')
    chat_id = Column(Integer)
    transaction_id = Column(String, unique=True)
    merchant_id = Column(String)
    date_create = Column(DateTime)
    date_update = Column(DateTime)
    category = Column(String)
    subcategory = Column(String)
    amount = Column(BigInteger)
    commission = Column(BigInteger)
    cashback = Column(BigInteger)
    currency_code = Column(SmallInteger)
    is_income = Column(Boolean)
    description = Column(String)
    status = Column(SmallInteger)
    type = Column(String)
    card_balance = Column(BigInteger)
    balance = Column(BigInteger, default=0)
    is_add_in_sheet = Column(Boolean)
    add_in_sheet_id = Column(String)
    date_add_in_sheet = Column(DateTime)
