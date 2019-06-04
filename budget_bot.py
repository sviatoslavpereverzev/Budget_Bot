from setting import *
import telebot
from telebot import types
import json
import logging
from database import DB
from datetime import datetime, timedelta
import calendar

MAX_LEN_NAME_CATEGORY = 25
bot = telebot.TeleBot(TOKEN)
db = DB()


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


@bot.message_handler(commands=['add'])
def add(message):
    print('add')
    try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass
    data = json.dumps({'f': 'amount'})
    categories = db.get_category(message.from_user.id)
    buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in categories.items()}
    keyboard_inline(message, bot, 'Выбери категорию:', buttons_name, callback_key='cat', previous_data=data)


@bot.message_handler(commands=['settings'])
def settings(message):
    print('settings')

    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    data = json.dumps({'f': 'set_stng'})
    buttons_name = {1: 'Добавить', 2: 'Удалить', 3: 'Получить ссылку на Google таблицу',
                    4: 'Изменить ссылку на Google таблицу', 5: 'Отмена'}
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

    db.add_user(message)


@bot.message_handler(commands=['help'])
def help(message):
    print(message.json)


def get_amount(call):
    print('get_amount')

    callback_data = json.loads(call.data)
    categories = db.get_category(call.from_user.id)
    subcategories_dict = categories.get(callback_data.get('cat', ), {}).get('subcategories', {})

    if subcategories_dict and 'sub' not in callback_data:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        subcategories_dict.items()}
        keyboard_inline(call.message, bot, 'Выберите подкатегорию:', buttons_name, callback_key='sub',
                        previous_data=call.data)

    else:
        category_name = categories.get(callback_data.get('cat'), {}).get('name')
        subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')
        if subcategories_dict:
            subcategory_name = f' Подкатегория: {subcategory_name}.'
        else:
            subcategory_name = ''
        text_message = f'Категория: {category_name}.{subcategory_name} Сумма: '
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        if category_name is None:
            bot.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')
        else:
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
        sheets_id = db.get_google_sheets_id(call.from_user.id)
        if sheets_id is None:
            bot.send_message(chat_id=call.message.chat.id, text='Cсылка на Google таблицу не установленна')
        else:
            bot.send_message(chat_id=call.message.chat.id, text='Ваша ссылка на Google таблицу:\n'
                                                                'https://docs.google.com/spreadsheets/d/' + sheets_id)
    elif func_id == 4:
        bot.send_message(chat_id=call.message.chat.id, text='Вставьте ссылку на вашу Google таблицу:',
                         reply_markup=types.ForceReply())
    elif func_id == 11:
        buttons_name = {31: 'Доходы', 32: 'Расходы', }
        keyboard_inline(call.message, bot, 'Выберите тип категории:', buttons_name, callback_key='cat',
                        previous_data=call.data, )
    elif func_id == 12:
        categories = db.get_category(call.from_user.id)

        data = json.dumps({'f': 'add_s'})
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        keyboard_inline(call.message, bot, 'Выберите категорию:', buttons_name, callback_key='cat',
                        previous_data=data)
    elif func_id == 21:
        categories = db.get_category(call.from_user.id)

        data = json.dumps({'f': 'del', 'af': 1, 'a': 1})
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        keyboard_inline(call.message, bot, 'Удалить категорию:', buttons_name, callback_key='cat',
                        previous_data=data)

    elif func_id == 22:
        categories = db.get_category(call.from_user.id)
        data = json.dumps({'f': 'dels'})
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        categories.items()}
        keyboard_inline(call.message, bot, 'Выберите категорию:', buttons_name, callback_key='cat',
                        previous_data=data)
    elif func_id == 31 or func_id == 32:
        if db.can_add_category(call.from_user.id):
            bot.send_message(chat_id=call.message.chat.id,
                             text='Введите новое имя категории {}:'.format('доходов' if func_id == 31 else 'расходов'),
                             reply_markup=types.ForceReply())
        else:
            bot.send_message(chat_id=call.message.chat.id, text='Нельзя добавлять больше 15 категорий!')


def prepare_report(call, report_for=None, exact_month=None):
    print('prepare_report')

    c = calendar.Calendar()
    month = datetime.now().month
    year = datetime.now().year
    message_text = None

    if report_for == 1:
        time_to = datetime.now().strftime('%Y-%m-%d ') + '23:59:59'
        time_from = datetime.now().strftime('%Y-%m-%d ') + '00:00:00'
        report_ = db.generate_report(time_from, time_to, call.from_user.id)
        if report_:
            message_text = f'{"-"*50}\nОтчет за день: \n\n{report_}'

    elif report_for == 2:
        time_from = list(week for week in c.monthdatescalendar(year, month) if datetime.now().date() in week)[0][0]
        time_to = list(week for week in c.monthdatescalendar(year, month) if datetime.now().date() in week)[0][-1]
        report_ = db.generate_report(time_from, time_to, call.from_user.id)
        if report_:
            message_text = f'{"-"*50}\nОтчет за неделю: \n\n{report_}'

    elif report_for == 3:
        time_from = [day for day in c.itermonthdates(year, month) if day.month == 5][0]
        time_to = [day for day in c.itermonthdates(year, month) if day.month == 5][-1]
        report_ = db.generate_report(time_from, time_to, call.from_user.id)
        if report_:
            message_text = f'{"-"*50}\nОтчет за месяц: \n\n{report_}'

    elif exact_month:
        month = int(exact_month.split('_')[0])
        year = int(str(datetime.now().year)[:-1] + exact_month.split('_')[1])

        time_from = [day for day in c.itermonthdates(year, month) if day.month == month][0].strftime(
            '%Y-%m-%d 00:00:00')
        time_to = [day for day in c.itermonthdates(year, month) if day.month == month][-1].strftime('%Y-%m-%d 23:59:59')
        report_ = db.generate_report(time_from, time_to, call.from_user.id)
        if report_:
            message_text = f'{"-"*50}\nОтчет за месяц: \n\n{report_}'

    if message_text:
        bot.send_message(chat_id=call.message.chat.id,
                         text=message_text)
    else:
        bot.send_message(chat_id=call.message.chat.id,
                         text='Нет затрат за этот период')


def get_report(call):
    print('get_report')

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Дальше')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    report_for = callback_data.get('cat')

    if report_for == 4:
        if 'date' not in callback_data:
            buttons_name = db.get_report_month(call.from_user.id)
            keyboard_inline(call.message, bot, 'Выберите подкатегорию:', buttons_name, callback_key='date',
                            previous_data=call.data)
        else:
            exact_month = callback_data.get('date')
            prepare_report(call, exact_month=exact_month)
    else:
        prepare_report(call, report_for)


def delete_category(call):
    print('delete')

    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    categories = db.get_category(call.from_user.id)
    category_name = categories.get(callback_data.get('cat', {})).get('name', 'Name Error')
    if callback_data.get('an'):
        if db.delete_category(call.message, callback_data.get('cat')):
            bot.send_message(chat_id=call.message.chat.id, text=f'Удалил категорию: {category_name}')
        else:
            bot.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')


def delete_subcategories(call):
    print('delete_subcategories')

    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    categories = db.get_category(call.from_user.id)
    subcategories_dict = categories.get(callback_data.get('cat', ), {}).get('subcategories')
    if not subcategories_dict:
        bot.send_message(chat_id=call.message.chat.id, text='Нет подкатегорий')
    elif subcategories_dict and 'sub' not in callback_data:
        data = json.loads(call.data)
        data['af'] = 1
        data['a'] = 2
        buttons_name = {button_id: button_name.get('name', 'Name Error') for button_id, button_name in
                        subcategories_dict.items()}
        keyboard_inline(call.message, bot, 'Выбери подкатегорию:', buttons_name, callback_key='sub',
                        previous_data=json.dumps(data))
    elif callback_data.get('an'):
        subcategory_name = subcategories_dict.get(callback_data.get('sub', ), {}).get('name', 'Name Error')
        if db.delete_subcategory(call, callback_data.get('cat'), callback_data.get('sub')):
            bot.send_message(chat_id=call.message.chat.id, text=f'Удалил подкатегорию: {subcategory_name}')
        else:
            bot.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так (')


def ask_again(call):
    print('ask_again')

    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    callback_data = json.loads(call.data)
    categories = db.get_category(call.from_user.id)
    category_name = categories.get(callback_data.get('cat', ), {}).get('name', 'Name Error')
    subcategories_name = categories.get(callback_data.get('cat', ), {}).get('subcategories', {}).get(
        callback_data.get('sub', ), {}).get('name', 'Name Error')
    t = {1: f'Удалить категорию {category_name}?',
         2: f'Удалить подкатегорию {subcategories_name}?'}

    buttons_name = {1: 'Да', 0: 'Нет'}
    keyboard_inline(call.message, bot, t.get(callback_data.get('a'), 'Вы уверенны?'), buttons_name,
                    callback_key='an', previous_data=call.data)


def add_subcategory(call):
    print('add_subcategory')

    callback_data = json.loads(call.data)
    categories = db.get_category(call.from_user.id)
    category_name = categories.get(callback_data.get('cat'), {}).get('name')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    if db.can_add_subcategory(call):
        bot.send_message(chat_id=call.message.chat.id, text=f'Категория: {category_name}. '
                                                            f'Введите новое имя подкатегории:',
                         reply_markup=types.ForceReply())
    else:
        bot.send_message(chat_id=call.message.chat.id, text='Нельзя добавлять больше 6 подкатегорий!')


FUNC = {'amount': get_amount,
        'set_stng': set_settings,
        'get_rp': get_report,
        'del': delete_category,
        'dels': delete_subcategories,
        'a': ask_again,
        'add_s': add_subcategory, }


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    print('callback_inline')

    try:
        if json.loads(call.data).get('af') and 'an' not in json.loads(call.data):
            ask_again(call)
        else:
            func = FUNC.get(json.loads(call.data).get('f'), lambda *args, **kwargs: False)
            func(call)
    except Exception as e:
        print(e)


@bot.message_handler(content_types=['text'])
def text(message):
    print('text')

    if message.reply_to_message:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass
        if message.reply_to_message.text.find('Категория') != -1 and message.reply_to_message.text.find('Сумма:') != -1:
            if message.reply_to_message.text.find(' грн.') != -1:
                bot.send_message(chat_id=message.chat.id,
                                 text='Уже есть')
            else:
                try:
                    amount = round(float(message.text), 2)
                    if amount < 92233720368547758.07:
                        if db.add_data(message):
                            bot.send_message(chat_id=message.chat.id,
                                             text=f'Добавил:\n{message.reply_to_message.text} {message.text} грн.')
                        else:
                            bot.send_message(chat_id=message.chat.id, text='Видимо у меня проблемы, попробуй позже')

                    else:
                        bot.send_message(chat_id=message.chat.id,
                                         text='Это слишком большая сумма.')

                except:
                    bot.send_message(chat_id=message.chat.id,
                                     text='Чет не то с суммой, давай по новой!\n'
                                          'К примеру: 1 грн 55 копеек нужно накисать как 1.55')
            add(message)
        if message.reply_to_message.text.find('Вставьте ссылку на вашу Google таблицу:') != -1:
            id_sheet = db.set_google_sheets_id(message)
            if id_sheet:
                bot.send_message(chat_id=message.chat.id,
                                 text=f'Заменил ссылку на: https://docs.google.com/spreadsheets/d/{id_sheet}')
            else:
                bot.send_message(chat_id=message.chat.id, text='Что-то не так c сылкой.')

        if message.reply_to_message.text.find('Введите новое имя категории') != -1:
            if message.text.isalpha():
                if len(message.text) >= MAX_LEN_NAME_CATEGORY:
                    bot.send_message(chat_id=message.chat.id,
                                     text=f'Очень длинное название ')
                # Длина не больше
                elif db.add_category(message):
                    bot.send_message(chat_id=message.chat.id,
                                     text=f'Добавил категорию {message.text}.')
                else:
                    bot.send_message(chat_id=message.chat.id, text='Что-то пошло не так (')
            else:
                bot.send_message(chat_id=message.chat.id,
                                 text='Используйте только буквы для названия категории без пробелов!\n'
                                      'Попробуйте снова.')

        if message.reply_to_message.text.find('Введите новое имя подкатегории:') != -1:
            if message.text.isalpha():
                if len(message.text) >= MAX_LEN_NAME_CATEGORY:
                    bot.send_message(chat_id=message.chat.id,
                                     text=f'Очень длинное название ')
                elif db.add_subcategory(message):
                    bot.send_message(chat_id=message.chat.id,
                                     text=f'Добавил подкатегорию {message.text}.')
                else:
                    bot.send_message(chat_id=message.chat.id,
                                     text='Что-то не так')
            else:
                bot.send_message(chat_id=message.chat.id, text='Используйте только буквы для названия подкатегории!\n'
                                                               'Попробуйте снова.')


def main():
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


if __name__ == '__main__':
    main()
