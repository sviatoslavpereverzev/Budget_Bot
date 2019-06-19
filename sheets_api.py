# -*- coding: utf-8 -*-
from configparser import ConfigParser
import os
import httplib2
import logging
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pprint import pprint
import pickle
from datetime import datetime
from database import DB
from cryptography.fernet import Fernet


class SheetsApi:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/drive']
        self.credentials_file = None
        self.service = None

        self.model_spreadsheet_id = None
        self.model_sheets_id = None

        self.config = ConfigParser()
        self.set_settings()

    def set_settings(self):
        self.config.read(os.path.dirname(os.path.abspath(__file__)) + '/app.ini')
        self.model_spreadsheet_id = self.config.get('SHEETS_API', 'model_spreadsheet_id')
        self.model_sheets_id = [int(sheets_id) for sheets_id in
                                self.config.get('SHEETS_API', 'model_sheets_id').split(',')]
        pass

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

        self.driveService = apiclient.discovery.build('drive', 'v3', credentials=creds)
        self.service = apiclient.discovery.build('sheets', 'v4', credentials=creds)
        pprint(self.service)

    def create_sheet(self, db):
        users_id = db.create_sheets_for()
        for user_id in users_id:
            request_body = {
                'properties': {
                    'title': self.encrypt(user_id[0]),
                    'locale': 'uk',
                    'timeZone': 'Europe/Kiev'
                }
            }
            try:
                request = self.service.spreadsheets().create(body=request_body)
                response = request.execute()
            except Exception as e:
                logging.error(f'Error create spreadsheet for user {user_id[0]}. Error: {e}')
                continue

            new_spreadsheet_id = response['spreadsheetId']
            spreadsheet_url = response['spreadsheetUrl']

            # copy to spreadsheet
            request_body = {
                'destinationSpreadsheetId': new_spreadsheet_id
            }
            sheets_name = {}
            error_copy_to_spreadsheet = None
            for sheet_id in self.model_sheets_id:
                try:
                    request = self.service.spreadsheets().sheets().copyTo(spreadsheetId=self.model_spreadsheet_id,
                                                                          sheetId=sheet_id,
                                                                          body=request_body)
                    response = request.execute()
                except Exception as e:
                    logging.error(f'Error at copy sheets {sheet_id} for user {user_id[0]}. Error: {e}')
                    error_copy_to_spreadsheet = True
                    break
                else:
                    sheets_name.update({response['sheetId']: response['title'].replace('Копія аркуша ', '')})

            if error_copy_to_spreadsheet:
                continue

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
            request_body['requests'].append({
                'deleteSheet': {
                    'sheetId': 0
                }
            })
            try:
                self.service.spreadsheets().batchUpdate(spreadsheetId=new_spreadsheet_id,
                                                        body=request_body).execute()
            except Exception as e:
                logging.error(f'Error at rename sheets and delete sheet1 for user {user_id[0]}. Error: {e}')

            # open permission
            try:
                self.driveService.permissions().create(
                    fileId=new_spreadsheet_id,
                    body={'type': 'anyone', 'role': 'writer'},
                    fields='*'
                ).execute()
            except Exception as e:
                logging.error(f'Error opening access rightsfor user {user_id[0]}. Error: {e}')
                continue

            if not db.set_google_sheets_id(spreadsheet_url, user_id[0]):
                logging.error(f'Error set google sheets id for user {user_id[0]}. Error: {e}')

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
        for i in range(1, 101):
            request_body = {
                "majorDimension": "ROWS",
                "range": "Data",
                "values": [
                    [
                        datetime.now().date().strftime('%Y-%m-%d'),
                        datetime.now().time().strftime('%H:%M:%S'),
                        20,
                        'Питание',
                        None,
                        34.5 * i,
                        'Доход'
                    ]
                ]
            }
            request = self.service.spreadsheets().values().append(
                spreadsheetId='1x4KvEWVTjONCpBEsleBRGX_EOqhDfiGbDb_aLaOuGO8', range='Data',
                body=request_body,
                valueInputOption='USER_ENTERED')

            response = request.execute()

            pprint(response)

    def can_connect_sheet(self, db):
        return True

    def main(self):
        db = DB()
        self.set_service()
        self.create_sheet(db)
        # self.can_connect_sheet(db)
        # self.add_data(db)


sheet_api = SheetsApi()
sheet_api.main()
# x = sheet_api.encrypt(529088251)
# print(x)
# print(sheet_api.decrypt(x))
# sheet_api.set_service()
# # sheet_api.create_sheet()
# sheet_api.set_service()
# sheet_api.add_data('')
