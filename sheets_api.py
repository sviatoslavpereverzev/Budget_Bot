# -*- coding: utf-8 -*-
from configparser import ConfigParser
import os
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pprint import pprint
import pickle


class SheetsApi:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/drive']
        self.credentials_file = None
        self.service = None
        self.config = ConfigParser()
        self.set_settings()

    def set_settings(self):
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

    def create_sheet(self):

        # create spreadsheet
        print('create spreadsheet')
        request_body = {
            'properties': {
                'title': 'Саша сучка а Славик красавчик',
                'locale': 'ru_RU',
                'timeZone': 'Europe/Helsinki'
            }
        }
        request = self.service.spreadsheets().create(body=request_body)
        response = request.execute()
        new_spreadsheet_id = response['spreadsheetId']
        spreadsheet_url = response['spreadsheetUrl']
        pprint(response)

        # copy to spreadsheet
        print('copy to spreadsheet')
        model_spreadsheet_id = '1IxC2KFWu-ywL7K4k_db9gl7bIpIphiUXbVcJguhrbG8'
        request_body = {
            'destinationSpreadsheetId': new_spreadsheet_id
        }
        sheets_id = [1446449488, 2102683703, 866833467, 1215147421]
        sheets_name = {}
        for sheet_id in sheets_id:
            request = self.service.spreadsheets().sheets().copyTo(spreadsheetId=model_spreadsheet_id, sheetId=sheet_id,
                                                                  body=request_body)
            response = request.execute()
            sheets_name.update({response['sheetId']: response['title'].replace(' (копия)', '')})
            pprint(response)

        # rename sheets
        print('rename sheets and delete sheet1')
        request_body = {
            'requests': [
            ]
        }
        # sheets_name = {1321156125: 'Расходы', 1692779675: 'Баланс', 379428490: 'Доходы', 1765887935: 'Data'}
        for sheet_id, sheet_name in sheets_name.items():
            # print(sheet_id, sheet_name)
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
        request = self.service.spreadsheets().batchUpdate(spreadsheetId=new_spreadsheet_id,
                                                          body=request_body)
        response = request.execute()
        pprint(response)

        # open permission
        print('open permission')
        response = self.driveService.permissions().create(
            fileId=new_spreadsheet_id,
            body={'type': 'anyone', 'role': 'writer'},  # доступ на чтение кому угодно
            fields='*'
        ).execute()
        pprint(response)

        print(spreadsheet_url)


sheet_api = SheetsApi()
sheet_api.set_service()
sheet_api.create_sheet()
