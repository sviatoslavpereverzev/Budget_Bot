# -*- coding: utf-8 -*-
import os
import logging
import time
import json
import pickle
from configparser import ConfigParser

import apiclient.discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

from database import DB
from budget_bot import send_message_telegram


class SheetsApi:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/drive']
        self.sheet_service = None
        self.drive_service = None

        # chat id where bot error messages are sent
        self.chat_id_error_notification = None

        # table ID with templates
        self.model_spreadsheet_id = None
        # pattern sheet ID list
        self.model_sheets_id = None
        # ID list Data
        self.data_sheets_id = None
        # email bot to which to open access to the table
        self.email_budget_bot = None

        self.config = ConfigParser()
        self.set_settings()

    def set_settings(self):
        self.config.read(os.path.dirname(os.path.abspath(__file__)) + '/app.ini')
        self.chat_id_error_notification = self.config.getint('BUDGET_BOT', 'chat_id_error_notification')
        self.model_spreadsheet_id = self.config.get('SHEETS_API', 'model_spreadsheet_id')
        self.model_sheets_id = [int(sheets_id) for sheets_id in
                                self.config.get('SHEETS_API', 'model_sheets_id').split(',')]
        self.data_sheets_id = [self.config.getint('SHEETS_API', 'data_sheets_id')]
        self.email_budget_bot = self.config.get('SHEETS_API', 'email_budget_bot')

    def set_service(self):
        """Starting Google Services"""

        creds = None
        if os.path.exists(os.path.dirname(os.path.realpath(__file__)) + '/private/token.pickle'):
            with open(os.path.dirname(os.path.realpath(__file__)) + '/private/token.pickle', 'rb') as token:
                creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.dirname(os.path.realpath(__file__)) + '/private/credentials.json', self.scope)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open(os.path.dirname(os.path.realpath(__file__)) + '/private/token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.drive_service = apiclient.discovery.build('drive', 'v3', credentials=creds)
        self.sheet_service = apiclient.discovery.build('sheets', 'v4', credentials=creds)

    def create_sheet(self, db):
        """Creating a new table for the user and adding necessary sheets"""

        # create sheet
        users_id = db.create_sheets_for()
        for user_id in users_id:
            request_body = {
                'properties': {
                    'title': f'{str(int(time.time()))}_{str(user_id)}',
                    'locale': 'uk',
                    'timeZone': 'Europe/Kiev'
                }
            }
            try:
                request = self.sheet_service.spreadsheets().create(body=request_body)
                response = request.execute()
            except HttpError as e:
                logging.error(f'Error create spreadsheet for user {user_id}. Error: {e}')
                continue

            new_spreadsheet_id = response['spreadsheetId']
            spreadsheet_url = response['spreadsheetUrl']

            if not db.set_google_sheets_id(user_id, spreadsheet_url):
                logging.error(f'Error set google sheets id for user {user_id}. Error: {e}')

            if not self.copy_model_sheets(user_id, new_spreadsheet_id, self.model_sheets_id + self.data_sheets_id,
                                          dell_sheet1=True):
                continue

            # open permission
            try:
                self.drive_service.permissions().create(
                    fileId=new_spreadsheet_id,
                    body={'type': 'anyone', 'role': 'writer'},
                    fields='*'
                ).execute()
                message_text = f'Для вас созданна новая таблица:\n{spreadsheet_url}\n'
                send_message_telegram(message_text, user_id)
            except HttpError as e:
                logging.error(f'Error opening access rightsfor user {user_id}. Error: {e}')
                continue

    def copy_model_sheets(self, user_id, spreadsheet_id, sheets_id, dell_sheet1=False):
        """Copy sheets from the base model"""

        request_body_copy = {
            'destinationSpreadsheetId': spreadsheet_id
        }
        sheets_name = {}
        error_copy_to_spreadsheet = None
        for sheet_id in sheets_id:
            try:
                request = self.sheet_service.spreadsheets().sheets().copyTo(spreadsheetId=self.model_spreadsheet_id,
                                                                            sheetId=sheet_id,
                                                                            body=request_body_copy)
                response = request.execute()
            except HttpError as e:
                logging.error(f'Error at copy sheets {sheet_id} for user {user_id}. Error: {e}')
                error_copy_to_spreadsheet = True
                continue
            else:
                sheets_name.update(
                    {response['sheetId']: response['title'].replace('Копія аркуша ', '').replace(' (копия)', '')})

            # rename sheets
            request_body = {
                'requests': [
                ]
            }
            for sheet, sheet_name in sheets_name.items():
                request_body['requests'].append({
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet,
                            'title': sheet_name,
                            'gridProperties': {
                                'columnCount': 26,
                                'rowCount': 1000
                            }
                        },
                        'fields': '*'
                    },
                })

            # delete first sheet
            if dell_sheet1:
                request_body['requests'].append({
                    'deleteSheet': {
                        'sheetId': 0
                    }
                })
                dell_sheet1 = False
            try:
                self.sheet_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,
                                                              body=request_body).execute()
            except HttpError as e:
                logging.error(f'Error at rename sheets and delete sheet1 for user {user_id}. Error: {e}')

        return True if not error_copy_to_spreadsheet else False

    def add_data(self, db):
        """Added data in google sheet"""

        users_id = db.add_data_in_sheet()
        for user_id in users_id:
            all_data = db.get_data(user_id)
            #  list of all id records that have been added to sheet
            added_ids = []

            # created request
            request_body = {
                'majorDimension': 'ROWS',
                'range': 'Data',
                'values': []}
            for data in all_data:
                added_ids.append(str(data[0]))
                date = data[1].strftime('%Y-%m-%d')
                time = data[1].strftime('%H:%M:%S')
                week = data[1].isocalendar()[1]
                category = data[2]
                subcategory = data[3] if data[3] != 'None' else ''
                amount = data[4]
                type_ = 'Доход' if data[5] else 'Расход'

                request_body['values'].append([date, time, week, category, subcategory, amount, type_])

            spreadsheet_id = db.get_google_sheets_id(user_id)

            # added data in sheet
            try:
                request = self.sheet_service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range='Data',
                                                                            body=request_body,
                                                                            valueInputOption='USER_ENTERED').execute()
            except HttpError as e:
                logging.error(f'Error at add data in sheet_id: {spreadsheet_id} for user {user_id}.\n Error: {e}\n'
                              f'Error detail: {e.content.decode("utf-8")}')

                error_detail = json.loads(e.content)
                if error_detail['error']['errors'][0]['message'] == 'Unable to parse range: Data':
                    if self.copy_model_sheets(user_id, spreadsheet_id, self.data_sheets_id):
                        message_text = f'Создан новый листа Data в таблице: ' \
                                       f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}.\n' \
                                       f'Пожалуйста не удаляйте и не переименовывайте этот лист.'
                        send_message_telegram(message_text, user_id)
                    else:
                        send_message_telegram('Budget_bot Error,\n Error:' + e.content.decode('utf-8'),
                                              self.chat_id_error_notification)
                        logging.error('Budget_bot Error,\n Error:' + e.content.decode('utf-8'))
                    continue

            # market data as added in database
            if not db.set_data_added(user_id, added_ids, spreadsheet_id):
                message_text = f'Error at add data in sheet_id: {spreadsheet_id} for user {user_id}.\n' \
                               f'Error: Records were not marked as added.'
                logging.error(message_text)
                send_message_telegram('Budget_bot Error,\n' + message_text, self.chat_id_error_notification)

    def change_sheet_id(self, db):
        """Change one table to another"""

        users_id = db.change_sheet_id()
        for user_id in users_id:
            spreadsheet_id = db.get_google_sheet_id_change(user_id)

            # access check
            try:
                request = self.sheet_service.spreadsheets().get(spreadsheetId=spreadsheet_id)
                response = request.execute()
            except HttpError as e:
                error_detail = json.loads(e.content)
                if error_detail['error']['code'] == 403 and error_detail['error']['status'] == 'PERMISSION_DENIED':
                    message_text = f'Внимание, таблица не изменена!\n' \
                                   f'Нет доступа к таблице: https://docs.google.com/spreadsheets/d/{spreadsheet_id}.\n' \
                                   f'Пожалуйста перейдите по ссылке на вашу таблицу, зайдите в "Настройки Доступа" и ' \
                                   f'откройте доступ на редавкирование для {self.email_budget_bot}, для того чтоб ' \
                                   f'Budget Bot мог добавлять новые записи в таблицу, затем снова повторите ' \
                                   f'изменение таблицы в настройках.'
                    send_message_telegram(message_text, user_id)
                    db.reset_google_sheet_id_change(user_id)
                    continue

            # data sheet check
            if 'Data' in (name['properties']['title'] for name in response['sheets']):
                message_text = f'Внимание, таблица не изменена!\n Уже есть лист Data в таблице: ' \
                               f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}.\n' \
                               f'Пожалуйста переименуйте или удалите лист Data затем снова повторите изменение ' \
                               f'таблицы в настройках.'
                send_message_telegram(message_text, user_id)
                db.reset_google_sheet_id_change(user_id)
            else:
                if self.copy_model_sheets(user_id, spreadsheet_id, self.data_sheets_id):
                    if db.set_google_sheets_id(user_id, spreadsheet_id):
                        message_text = f'Таблицв заменена на : https://docs.google.com/spreadsheets/d/{spreadsheet_id}.'
                        db.reset_google_sheet_id_change(user_id)
                        send_message_telegram(message_text, user_id)
                    else:
                        logging.error(f'Ошибка при изменении таблицы {spreadsheet_id}')

    def main(self):
        logging.error('Start Sheet API')
        db = DB()
        self.set_service()
        while True:
            self.create_sheet(db)
            self.change_sheet_id(db)
            self.add_data(db)
            time.sleep(0.2)


if __name__ == '__main__':
    sheet_api = SheetsApi()
    sheet_api.main()
