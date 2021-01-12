# -*- coding: utf-8 -*-
import requests
import xml.etree.cElementTree as ET
import hashlib
from hashlib import md5, sha1


class PrivatBankClient:

    def get_balance(self):
        xml_request = ET.Element('request')
        xml_merchant = ET.SubElement(xml_request, 'merchant')
        xml_id = ET.SubElement(xml_merchant, 'id')
        xml_signature = ET.SubElement(xml_merchant, 'signature')
        xml_data = ET.SubElement(xml_request, 'data')
        xml_oper = ET.SubElement(xml_data, 'oper')
        xml_wait = ET.SubElement(xml_data, 'wait')
        xml_test = ET.SubElement(xml_data, 'test')
        xml_payment = ET.SubElement(xml_data, 'payment')
        xml_prop_1 = ET.SubElement(xml_payment, 'prop')
        xml_prop_2 = ET.SubElement(xml_payment, 'prop')

        xml_id.text = '147113'
        xml_oper.text = 'cmt'
        xml_wait.text = '30'
        xml_test.text = '1'
        xml_payment.set('id', '')
        xml_prop_1.set('name', 'cardnum')
        xml_prop_1.set('value', '5168745010513643')
        xml_prop_2.set('name', 'country')
        xml_prop_2.set('value', 'UA')

        xml_signature.text = self.get_sign(ET.tostring(xml_data))

        data = ET.tostring(xml_request, encoding='utf-8')
        response = requests.post('https://api.privatbank.ua/p24api/balance', data=data)
        #
        # print(response)
        print(response.text)

    def get_sign(self, data):
        point_token = 'lb2yOXSi2iHyqh0z0EF8Fp3ow9nXDydY'
        signature_md5 = md5((data.decode('utf-8')[6:-7] + point_token).encode('utf-8')).hexdigest()
        signature_done = sha1(signature_md5.encode('utf-8')).hexdigest()
        return signature_done

    def get_cost_statement(self):
        xml_request = ET.Element('request')
        xml_merchant = ET.SubElement(xml_request, 'merchant')
        xml_id = ET.SubElement(xml_merchant, 'id')
        xml_signature = ET.SubElement(xml_merchant, 'signature')
        xml_data = ET.SubElement(xml_request, 'data')
        xml_oper = ET.SubElement(xml_data, 'oper')
        xml_wait = ET.SubElement(xml_data, 'wait')
        xml_test = ET.SubElement(xml_data, 'test')
        xml_payment = ET.SubElement(xml_data, 'payment')
        # xml_prop_1 = ET.SubElement(xml_payment, 'prop')
        xml_prop_2 = ET.SubElement(xml_payment, 'prop')
        xml_prop_3 = ET.SubElement(xml_payment, 'prop')

        xml_id.text = '147113'
        xml_oper.text = 'cmt'
        xml_wait.text = '30'
        xml_test.text = '1'
        xml_payment.set('id', '')
        # xml_prop_1.set('name', 'cardnum')
        # xml_prop_1.set('value', '5168745010513643')
        xml_prop_2.set('name', 'sd')
        xml_prop_2.set('value', '28.03.2020')
        xml_prop_3.set('name', 'ed')
        xml_prop_3.set('value', '29.03.2020')

        xml_signature.text = self.get_sign(ET.tostring(xml_data))

        data = ET.tostring(xml_request, encoding='utf-8')
        print(data)
        response = requests.post('https://api.privatbank.ua/p24api/rest_fiz', data=data)
        #
        # print(response)
        print(response.text)


p = PrivatBankClient()
# p.get_balance()
p.get_cost_statement()