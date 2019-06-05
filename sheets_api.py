# -*- coding: utf-8 -*-
from configparser import ConfigParser
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials


class SheetsApi:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/spreadsheets',
                      'https://www.googleapis.com/auth/drive.file',
                      'https://www.googleapis.com/auth/drive']
        self.credentials_file = None
        self.service = None
        self.config = ConfigParser()
        self.set_settings()

    def set_settings(self):
        pass

    def set_service(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, self.scope)
        httpAuth = credentials.authorize(httplib2.Http())
        self.service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)

    def create_sheet(self):
        pass
