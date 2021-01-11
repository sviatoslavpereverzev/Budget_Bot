# -*- coding: utf-8 -*-
import os
import logging
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


def reset_creds():
    creds = None
    scope = ['https://www.googleapis.com/auth/drive']

    if os.path.exists(os.path.dirname(os.path.realpath(__file__)) + '/private/token.pickle'):
        with open(os.path.dirname(os.path.realpath(__file__)) + '/private/token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logging.error('Refresh creds')
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.dirname(os.path.realpath(__file__)) + '/private/credentials.json', scope)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(os.path.dirname(os.path.realpath(__file__)) + '/private/token.pickle', 'wb') as token:
            pickle.dump(creds, token)


if __name__ == '__main__':
    reset_creds()
