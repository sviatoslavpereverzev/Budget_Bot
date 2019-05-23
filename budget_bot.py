import telebot
from telebot import types
import json

TOKEN = '606473334:AAHtg8kuUGZKjzNGzP-UxazZoPvr4LWCcnY'
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


def keyboard_category(message, bot, text, buttons, callback_key, previous_data, qt_key=3):
    callback = json.loads(previous_data, encoding='utf-8')
    list_keys = []
    keyboard = types.InlineKeyboardMarkup(row_width=qt_key)
    for button_id, button_name in buttons.items():
        callback[callback_key] = button_id
        callback_data_ = json.dumps(callback)
        list_keys.append(types.InlineKeyboardButton(button_name, callback_data=callback_data_))
    keyboard.add(*list_keys)
    bot.send_message(message.chat.id, text, reply_markup=keyboard)


@bot.message_handler(commands=['add'])
def add(message):
    print('add')
    try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass
    categories = get_category(message)

    data = json.dumps({'func': 'subcat'})
    buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in categories.items()}
    keyboard_category(message, bot, 'Выбери категорию:', buttons_name, callback_key='cat_id', previous_data=data)


@bot.message_handler(commands=['settings'])
def settings(message):
    print('settings')

    data = json.dumps({'func': 'set_stng'})
    buttons_name = {1: 'Добавить', 2: 'Удалить', 3: 'Получить ID Google Sheets', 4: 'Установить ID Google Sheets'}
    keyboard_category(message, bot, 'Выбери настройки:', buttons_name, callback_key='cat_id', previous_data=data,
                      qt_key=1, )


@bot.message_handler(commands=['del'])
def settings(message):
    print('del')
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@bot.message_handler(commands=['report'])
def report(message):
    print('report')

    data = json.dumps({'func': 'get_rp'})
    buttons_name = {1: 'День', 2: 'Неделя', 3: 'Месяц', 4: 'Точная дата'}
    keyboard_category(message, bot, 'Отчет за:', buttons_name, callback_key='cat_id', previous_data=data, qt_key=1, )


def subcategories(call):
    categories = get_category(call.message)

    print('func subcategories')
    callback_data = json.loads(call.data)
    callback_data['func'] = 'amount'
    subcategories_dict = categories.get(callback_data.get('cat_id', ), {}).get('subcategories')
    if subcategories_dict:
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        subcategories_dict.items()}
        data = json.dumps(callback_data)
        keyboard_category(call.message, bot, 'Выбери подкатегорию:', buttons_name, callback_key='subcat_id',
                          previous_data=data)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
        text_message = 'Категория: {}, Cумма:'.format(
            (categories.get(callback_data.get('cat_id', {}))).get('name', 'Name Error'))
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(chat_id=call.message.chat.id, text=text_message, reply_markup=types.ForceReply())


def get_amount(call):
    categories = get_category(call.message)
    callback_data = json.loads(call.data)
    category = categories.get(callback_data.get('cat_id', {})).get('name', 'Name Error')
    print(categories.get(callback_data.get('cat_id', ), {}).get('subcategories', {}))
    subcategory = categories.get(callback_data.get('cat_id', ), {}).get('subcategories', {}).get(
        callback_data.get('subcat_id', ), {}).get('name', 'Name Error')
    text_message = 'Категория: {}, Подкатегория: {}, Сумма: '.format(category, subcategory)
    print(call.message.message_id)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    bot.send_message(chat_id=call.message.chat.id, text=text_message, reply_markup=types.ForceReply())


def set_settings(call):
    print('set_settings')
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    func_id = callback_data.get('cat_id')
    if func_id == 1:
        print('1')
    elif func_id == 2:
        print('2')
    elif func_id == 3:
        print('3')
    elif func_id == 4:
        print(4)


def get_report(call):
    pass


FUNC = {'subcat': subcategories,
        'amount': get_amount,
        'set_stng': set_settings,
        'get_rp': get_report, }


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    print('callback_inline')
    try:
        func = FUNC.get(json.loads(call.data).get('func'), lambda *args, **kwargs: False)
        func(call)
    except Exception as e:
        print(e)


@bot.message_handler(content_types=['text'])
def text(message):
    print('text')
    print(message)
    if message.reply_to_message and message.reply_to_message.text.find('Категория') != -1:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass
        if message.reply_to_message.text.find(' грн.') != -1:
            bot.send_message(chat_id=message.chat.id,
                             text='Уже есть')
        else:
            try:
                bot.send_message(chat_id=message.chat.id,
                                 text='{} {} грн.'.format(message.reply_to_message.text, message.text))

            except:
                bot.send_message(chat_id=message.chat.id,
                                 text='Чет не то с суммой, давай по новой!\n'
                                      'К примеру: 1 грн 55 копеек нужно накисать как 1.55')
        add(message)


bot.polling()
