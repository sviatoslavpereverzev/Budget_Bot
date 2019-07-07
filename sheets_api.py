# -*- coding: utf-8 -*-
from configparser import ConfigParser
import os
import json
import pickle
import httplib2
import logging
from datetime import datetime

import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

from pprint import pprint
import pickle
from datetime import datetime
from database import DB
from cryptography.fernet import Fernet

from budget_bot import send_message_telegram


class SheetsApi:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/drive']
        self.credentials_file = None
        self.service = None

        self.chat_id_error_notification = None

        self.model_spreadsheet_id = None
        self.model_sheets_id = None
        self.data_sheets_id = None
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
        # credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', self.scope)
        creds = None

        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.scope)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.drive_service = apiclient.discovery.build('drive', 'v3', credentials=creds)
        self.service = apiclient.discovery.build('sheets', 'v4', credentials=creds)
        pprint(self.service)

    def create_sheet(self, db):
        users_id = db.create_sheets_for()
        for user_id in users_id:
            request_body = {
                'properties': {
                    'title': self.encrypt(user_id),
                    'locale': 'uk',
                    'timeZone': 'Europe/Kiev'
                }
            }
            try:
                request = self.service.spreadsheets().create(body=request_body)
                response = request.execute()
            except Exception as e:
                logging.error(f'Error create spreadsheet for user {user_id}. Error: {e}')
                continue

            new_spreadsheet_id = response['spreadsheetId']
            spreadsheet_url = response['spreadsheetUrl']

            if not self.copy_model_sheets(user_id, new_spreadsheet_id, self.model_sheets_id + self.data_sheets_id):
                continue

            # open permission
            try:
                self.drive_service.permissions().create(
                    fileId=new_spreadsheet_id,
                    body={'type': 'anyone', 'role': 'writer'},
                    fields='*'
                ).execute()
            except Exception as e:
                logging.error(f'Error opening access rightsfor user {user_id}. Error: {e}')
                continue

            if not db.set_google_sheets_id(user_id, spreadsheet_url):
                logging.error(f'Error set google sheets id for user {user_id}. Error: {e}')

    def copy_model_sheets(self, user_id, spreadsheet_id, sheets_id, dell_sheet1=False):
        # copy to spreadsheet
        request_body = {
            'destinationSpreadsheetId': spreadsheet_id
        }
        sheets_name = {}
        error_copy_to_spreadsheet = None
        for sheet_id in sheets_id:
            try:
                request = self.service.spreadsheets().sheets().copyTo(spreadsheetId=self.model_spreadsheet_id,
                                                                      sheetId=sheet_id,
                                                                      body=request_body)
                response = request.execute()
            except Exception as e:
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
            for sheet_id, sheet_name in sheets_name.items():
                request_body['requests'].append({
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'title': sheet_name,
                            'gridProperties': {
                                'columnCount': 26,
                                'rowCount': 1000
                            }
                        },
                        'fields': '*'
                    },
                })
            if dell_sheet1:
                request_body['requests'].append({
                    'deleteSheet': {
                        'sheetId': 0
                    }
                })
            try:
                self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,
                                                        body=request_body).execute()
            except Exception as e:
                logging.error(f'Error at rename sheets and delete sheet1 for user {user_id}. Error: {e}')

            if not error_copy_to_spreadsheet:
                for sheet_id, sheet_name in sheets_name.items():
                    if sheet_name == 'Data':
                        print('Здксь установлю id в бд:', sheet_id)

        return True if not error_copy_to_spreadsheet else False

    @staticmethod
    def encrypt(data):
        with open(os.path.dirname(os.path.realpath(__file__)) + '/private/key_for_name.txt') as file:
            key = file.read().encode('utf-8')
        cipher = Fernet(key)
        return cipher.encrypt(str(data).encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt(data):
        with open(os.path.dirname(os.path.realpath(__file__)) + '/private/key_for_name.txt') as file:
            key = file.read().encode('utf-8')
        cipher = Fernet(key)
        return cipher.decrypt(data.encode('utf-8')).decode('utf-8')

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
                request = self.service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range='Data',
                                                                      body=request_body,
                                                                      valueInputOption='USER_ENTERED').execute()
            except HttpError as e:
                logging.error(f'Error at add data in sheet_id: {spreadsheet_id} for user {user_id}.\n Error: {e}')
                continue

            # market data as added in database
            if not db.set_data_added(user_id, added_ids, spreadsheet_id):
                message = f'Error at add data in sheet_id: {spreadsheet_id} for user {user_id}.\n' \
                          f'Error: Records were not marked as added.'
                logging.error(message)
                send_message_telegram('Budget_bot Error,\n' + message, self.chat_id_error_notification)

    def change_sheet_id(self, db):
        users_id = db.change_sheet_id()
        for user_id in users_id:
            spreadsheet_id = db.get_google_sheet_id_change(user_id)
            request = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id)
            try:
                response = request.execute()
            except HttpError as e:
                error_detail = json.loads(e.content)
                if error_detail['error']['code'] == 403 and error_detail['error']['status'] == 'PERMISSION_DENIED':
                    message_text = f'Внимание, таблица не изменена!\n' \
                                   f'Нет доступа к таблице: https://docs.google.com/spreadsheets/d/{spreadsheet_id}.\n' \
                                   f'Пожалуйста перейдите по ссылке на вашу таблицу, зайдите в "Настройки Доступа" и ' \
                                   f'откройте доступ для {self.email_budget_bot}, для того чтоб Budget Bot мог ' \
                                   f'добавлять новые записи в таблицу, затем снова повторите изменение таблицы ' \
                                   f'в настройках.'
                    send_message_telegram(message_text, user_id)
                    db.reset_google_sheet_id_change(user_id)
                    continue
            if 'Data' in (name['properties']['title'] for name in response['sheets']):
                message_text = f'Внимание, таблица не изменена!\n Уже есть лист Data в таблице: ' \
                               f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}.\n' \
                               f'Пожалуйста переименуйте или удалите лист Data затем снова повторите изменение ' \
                               f'таблицы в настройках.'
                send_message_telegram(message_text, user_id)
            else:
                if self.copy_model_sheets(user_id, spreadsheet_id, self.data_sheets_id):
                    message_text = f'Таблицв заменена на : https://docs.google.com/spreadsheets/d/{spreadsheet_id}.'
                    send_message_telegram(message_text, user_id)

    def main(self):
        db = DB()
        self.set_service()
        # self.create_sheet(db)
        # self.change_sheet_id(db)
        self.add_data(db)


sheet_api = SheetsApi()
sheet_api.main()
# x = sheet_api.encrypt(529088251)
# print(x)
# print(sheet_api.decrypt(x))
# sheet_api.set_service()
# # sheet_api.create_sheet()
# sheet_api.set_service()
# sheet_api.add_data('')
