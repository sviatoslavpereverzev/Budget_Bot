from setting import *
import telebot
from telebot import types
import json
import requests
from time import sleep, time

bot = telebot.TeleBot(TOKEN)


def get_category(message):
    category = {
        1: {'name': 'Питание',
            'subcategories': {1: {'name': 'Продукты'}, 2: {'name': 'Сладкое'}, 3: {'name': 'Прочее'}}},
        2: {'name': 'Заведения',
            'subcategories': {1: {'name': 'Кафе и рестораны'}, 2: {'name': 'Суши'}, 3: {'name': "McDonald's"},
                              4: {'name': 'Прочее'}}},
        3: {'name': 'Квартира',
            'subcategories': {1: {'name': 'Аренда'}, 2: {'name': 'Комуналка'}, 3: {'name': 'Прочее'}}},
        4: {'name': 'Транспорт',
            'subcategories': {1: {'name': 'Маршрутка'}, 2: {'name': 'Метро'}, 3: {'name': 'Такси'}}},
        5: {'name': 'Здоровье',
            'subcategories': {1: {'name': 'Кафе и рестораны'}, 2: {'name': 'Суши'}, 3: {'name': "McDonald's"},
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
    return category


def can_add_category(message):
    return True
    from random import randint
    return randint(0, 1)


def can_add_subcategory(message):
    return True
    from random import randint
    return randint(0, 1)


def get_report_month(message):
    return {1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май'}


def get_report_day(message):
    return {x: x for x in range(1, 32)}


def keyboard_inline(message, bot_, message_text, buttons, callback_key, previous_data, qt_key=3):
    callback = json.loads(previous_data, encoding='utf-8')
    list_keys = []
    keyboard = types.InlineKeyboardMarkup(row_width=qt_key)
    for button_id, button_name in buttons.items():
        callback[callback_key] = button_id
        callback_data_ = json.dumps(callback)
        list_keys.append(types.InlineKeyboardButton(button_name, callback_data=callback_data_))
    keyboard.add(*list_keys)
    bot_.send_message(message.chat.id, message_text, reply_markup=keyboard)


# def keyboard_category(message, data):
#     categories = get_category(message)
#     buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in categories.items()}
#     keyboard_inline(message, bot, 'Выбери категорию:', buttons_name, callback_key='cat', previous_data=data)
#
#
# def get_subcategories(message, data):
#     print('get_subcategories')
#     categories = get_category(message)
#     callback_data = json.loads(data)
#     subcategories_dict = categories.get(callback_data.get('cat', ), {}).get('subcategories')
#     buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
#                     subcategories_dict.items()}
#     keyboard_inline(message, bot, 'Выбери подкатегорию:', buttons_name, callback_key='sub', previous_data=data)


@bot.message_handler(commands=['add'])
def add(message):
    print('add')
    try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass
    data = json.dumps({'f': 'amount'})
    categories = get_category(message)
    buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in categories.items()}
    keyboard_inline(message, bot, 'Выбери категорию:', buttons_name, callback_key='cat', previous_data=data)


@bot.message_handler(commands=['settings'])
def settings(message):
    print('settings')

    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    data = json.dumps({'f': 'set_stng'})
    buttons_name = {1: 'Добавить', 2: 'Удалить', 3: 'Получить ID Google Sheets', 4: 'Установить ID Google Sheets'}
    keyboard_inline(message, bot, 'Выбери настройки:', buttons_name, callback_key='cat', previous_data=data,
                    qt_key=1, )


@bot.message_handler(commands=['report'])
def report(message):
    print('report')

    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    data = json.dumps({'f': 'get_rp'})
    buttons_name = {1: 'День', 2: 'Неделя', 3: 'Месяц', 4: 'Точная дата'}
    keyboard_inline(message, bot, 'Отчет за:', buttons_name, callback_key='cat', previous_data=data, qt_key=1, )


@bot.message_handler(commands=['start'])
def start(message):
    print('start')


@bot.message_handler(commands=['help'])
def help(message):
    print('help')


def get_amount(call):
    print('get_amount')
    callback_data = json.loads(call.data)
    categories = get_category(call.message)
    subcategories_dict = categories.get(callback_data.get('cat', ), {}).get('subcategories')

    if subcategories_dict and 'sub' not in callback_data:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        subcategories_dict.items()}
        keyboard_inline(call.message, bot, 'Выберите подкатегорию:', buttons_name, callback_key='sub',
                        previous_data=call.data)

    else:
        category_name = categories.get(callback_data.get('cat', {})).get('name', 'Name Error')
        subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')
        if subcategories_dict:
            subcategory_name = f' Подкатегория: {subcategory_name},'
        else:
            subcategory_name = ''
        text_message = f'Категория: {category_name},{subcategory_name} Сумма: '

        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(chat_id=call.message.chat.id, text=text_message, reply_markup=types.ForceReply())


def set_settings(call):
    print('set_settings')
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    func_id = callback_data.get('cat')
    if func_id == 1:
        buttons_name = {11: 'Категорию', 12: 'Подкатегорию', }
        keyboard_inline(call.message, bot, 'Добавить:', buttons_name, callback_key='cat',
                        previous_data=call.data, )
    elif func_id == 2:
        buttons_name = {21: 'Категорию', 22: 'Подкатегорию', }
        keyboard_inline(call.message, bot, 'Удалить:', buttons_name, callback_key='cat',
                        previous_data=call.data, )
    elif func_id == 3:
        bot.send_message(chat_id=call.message.chat.id, text='ID Google Sheets: '
                                                            'G28wZHaKSi7TAC8oOqTjthh8P-EEk_pa8PIirRwSDR4')
    elif func_id == 4:
        bot.send_message(chat_id=call.message.chat.id, text='Введите ID Google Sheets:',
                         reply_markup=types.ForceReply())
    elif func_id == 11:
        if can_add_category(call.message):
            bot.send_message(chat_id=call.message.chat.id, text='Введите новое имя категории:',
                             reply_markup=types.ForceReply())
        else:
            bot.send_message(chat_id=call.message.chat.id, text='Нельзя добавлять больше 15 категорий!')
    elif func_id == 12:
        categories = get_category(call.message)

        data = json.dumps({'f': 'add_s'})
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        keyboard_inline(call.message, bot, 'Выберите категорию:', buttons_name, callback_key='cat',
                        previous_data=data)
    elif func_id == 21:
        categories = get_category(call.message)

        data = json.dumps({'f': 'del', 'af': 1, 'ask': 1})
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        keyboard_inline(call.message, bot, 'Удалить категорию:', buttons_name, callback_key='cat',
                        previous_data=data)

    elif func_id == 22:
        categories = get_category(call.message)
        data = json.dumps({'f': 'dels'})
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        keyboard_inline(call.message, bot, 'Выберите категорию:', buttons_name, callback_key='cat',
                        previous_data=data)


def prepare_report(call, report_for=None, exact_day=None):
    if report_for == 1:
        message_text = 'Report day'
    elif report_for == 2:
        message_text = 'Report week'
    elif report_for == 3:
        message_text = 'Report month'
    elif exact_day:
        month = exact_day.get('month')
        day = exact_day.get('day')
        message_text = f'Report Day:{day} Month:{month}'
    else:
        message_text = 'Error Report'
    bot.send_message(chat_id=call.message.chat.id,
                     text=message_text)


def get_report(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    report_for = callback_data.get('cat')
    if report_for == 4:
        if 'mnth' not in callback_data:
            buttons_name = get_report_month(call.message)
            keyboard_inline(call.message, bot, 'Выберите подкатегорию:', buttons_name, callback_key='mnth',
                            previous_data=call.data)
        elif 'day' not in callback_data:
            buttons_name = get_report_day(call.message)
            keyboard_inline(call.message, bot, 'Выберите подкатегорию:', buttons_name, callback_key='day',
                            previous_data=call.data)
        else:
            exact_day = {'month': callback_data.get('mnth'), 'day': callback_data.get('day')}
            prepare_report(call, exact_day=exact_day)

    else:
        prepare_report(call, report_for)


def delete_category(call):
    print('delete')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    categories = get_category(call.message)
    category_name = categories.get(callback_data.get('cat', {})).get('name', 'Name Error')
    if callback_data.get('answ'):
        bot.send_message(chat_id=call.message.chat.id, text=f'Удалил категорию: {category_name}')


def delete_subcategories(call):
    print('delete_subcategories')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    categories = get_category(call.message)
    subcategories_dict = categories.get(callback_data.get('cat', ), {}).get('subcategories')
    if not subcategories_dict:
        bot.send_message(chat_id=call.message.chat.id, text='Нет подкатегорий')
    elif subcategories_dict and 'sub' not in callback_data:
        data = json.loads(call.data)
        data['af'] = 1
        data['ask'] = 2

        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        subcategories_dict.items()}
        keyboard_inline(call.message, bot, 'Выбери подкатегорию:', buttons_name, callback_key='sub',
                        previous_data=json.dumps(data))
    elif callback_data.get('answ'):
        subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')
        bot.send_message(chat_id=call.message.chat.id, text=f'Удалил подкатегорию: {subcategory_name}')


def ask_again(call):
    print('ask_again')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    categories = get_category(call.message)
    category_name = categories.get(callback_data.get('cat', ), {}).get('name', 'Name Error')
    subcategories_name = categories.get(callback_data.get('cat', ), {}).get('subcategories', {}).get(
        callback_data.get('sub', ), {}).get('name', 'Name Error')
    t = {1: f'Удалить категорию {category_name}?',
         2: f'Удалить подкатегорию {subcategories_name}?'}

    print(call.data)
    print(len(call.data))
    buttons_name = {1: 'Да', 0: 'Нет'}
    keyboard_inline(call.message, bot, t.get(callback_data.get('ask'), 'Вы уверенны?'), buttons_name,
                    callback_key='answ', previous_data=call.data)


def add_subcategory(call):
    print('add_subcategory')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    if can_add_subcategory(call.message):
        bot.send_message(chat_id=call.message.chat.id, text='Введите новое имя подкатегории:',
                         reply_markup=types.ForceReply())
    else:
        bot.send_message(chat_id=call.message.chat.id, text='Нельзя добавлять больше 6 подкатегорий!')


FUNC = {  # 'sub': subcategories,
    'amount': get_amount,
    'set_stng': set_settings,
    'get_rp': get_report,
    'del': delete_category,
    'dels': delete_subcategories,
    'ask': ask_again,
    'add_s': add_subcategory, }


def change_id_sheets(message):
    return True


def run_function(call):
    print('run_function')
    try:
        func = FUNC.get(json.loads(call.data).get('f'), lambda *args, **kwargs: False)
        func(call)
    except Exception as e:
        print(e)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    print('callback_inline')
    if json.loads(call.data).get('af') and 'answ' not in json.loads(call.data):
        print()
        print(call)
        print()
        ask_again(call)

    else:
        run_function(call)


@bot.message_handler(content_types=['text'])
def text(message):
    print('text')
    print(message)
    if message.reply_to_message:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass
    if message.reply_to_message.text.find('Категория') != -1:
        if message.reply_to_message.text.find(' грн.') != -1:
            bot.send_message(chat_id=message.chat.id,
                             text='Уже есть')
        else:
            try:
                bot.send_message(chat_id=message.chat.id,
                                 text='Добавил:\n{} {} грн.'.format(message.reply_to_message.text, int(message.text)))

            except:
                bot.send_message(chat_id=message.chat.id,
                                 text='Чет не то с суммой, давай по новой!\n'
                                      'К примеру: 1 грн 55 копеек нужно накисать как 1.55')
        add(message)
    if message.reply_to_message.text.find('Введите ID Google Sheets:') != -1:
        id_sheet = 'G28wZHaKSi7TAC8oOqTjthh8P-EEk_pa8PIirRwSDR4'
        if change_id_sheets(message):
            bot.send_message(chat_id=message.chat.id,
                             text='Изменил ID Google Sheets на: {}'.format(id_sheet))

    if message.reply_to_message.text.find('Введите новое имя категории:') != -1:
        bot.send_message(chat_id=message.chat.id,
                         text=f'Добавил категорию {message.text}.')

    if message.reply_to_message.text.find('Введите новое имя подкатегории:') != -1:
        bot.send_message(chat_id=message.chat.id,
                         text=f'Добавил подкатегорию {message.text}.')


bot.polling()
# last_send = 0
# while True:
#     try:
#         bot.polling()
#     except Exception as e:
#         if last_send + 60 < time():
#             response = requests.post(
#                 url='https://api.telegram.org/bot{}/sendMessage'.format(TOKEN_2),
#                 data={'chat_id': -326310326, 'text': 'Проблемы у Budget bot\n{}'.format(e)}
#             ).json()
#             last_send = time()
