# -*- coding: utf-8 -*-

import requests, base64, json, logging, os, time, sys, time

logging.basicConfig(level=logging.DEBUG)

class AdamosClient:

    BOOTSTRAP_AUTH = 'management/devicebootstrap:Fhdt1bb1f'
    C8Y_BOOTSTRAP_HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(BOOTSTRAP_AUTH.encode('utf-8')).decode('utf-8')
    }

    def __init__(self, url, tenant, deviceName, serial):
        self.currentActiveAlarms = {}
        self.C8Y_BASE = url
        self.C8Y_TENANT = tenant
        self.C8Y_HEADERS = {}
        self.DEVICE_ID = ''
        self.DEVICE_NAME = deviceName
        self.DEVICE_EXT_ID = serial


    def getDeviceCredentials(self,id):
        request = {
            'id': id
        }
        response = requests.post(self.C8Y_BASE + '/devicecontrol/deviceCredentials', headers=AdamosClient.C8Y_BOOTSTRAP_HEADERS, data=json.dumps(request))
        return response

    def getOperations(self):
        response = requests.get(self.C8Y_BASE + '/devicecontrol/operations?status=PENDING', headers=self.C8Y_HEADERS)
        return response.json()

    def updateOperation(self, operationId, update):
        response = requests.put(self.C8Y_BASE + '/devicecontrol/operations/' + str(operationId), headers=self.C8Y_HEADERS, data=json.dumps(update))
        #return response.json()

    def sendMeasurement(self, measurement):
        print(self.C8Y_BASE)
        print(self.C8Y_HEADERS)
        response = requests.post(self.C8Y_BASE + '/measurement/measurements', headers=self.C8Y_HEADERS, data=json.dumps(measurement))
        return response.json()

    def sendAlarm(self, alarm):
        response = requests.post(self.C8Y_BASE + '/alarm/alarms', headers=self.C8Y_HEADERS, data=json.dumps(alarm))
        self.currentActiveAlarms[response.json()['type']] = response.json()['id']
        return response.json()

    def acknowledgeAlarm(self, alarmId):
        alarm = {
            'status': 'ACKNOWLEDGED'
        }
        response = requests.put(self.C8Y_BASE + '/alarm/alarms/' + str(alarmId), headers=self.C8Y_HEADERS, data=json.dumps(alarm))
        return response.json()

    def clearAlarm(self, alarmId):
        alarm = {
            'status': 'CLEARED'
        }
        response = requests.put(self.C8Y_BASE + '/alarm/alarms/' + str(alarmId), headers=self.C8Y_HEADERS, data=json.dumps(alarm))
        return response.json()

    def sendEvent(self, event):
        response = requests.post(self.C8Y_BASE + '/event/events', headers=self.C8Y_HEADERS, data=json.dumps(event))
        return response.json()

    def runOperationsLoop(self):
        while True:
            try:
                operations = self.getOperations()
                for op in operations['operations']:
                    print(op)
                time.sleep(1)
            except:
                time.sleep(1)

    def createDevice(self):
        device = {
            'name': self.DEVICE_NAME,
            'c8y_IsDevice': {},
            'c8y_SupportedOperations': [ 'c8y_Command', 'c8y_Firmware' ],
            'com_cumulocity_model_Agent': {},
            'c8y_RequiredAvailability': {
                'responseInterval': 3
            },
            'c8y_Hardware': {
                'serialNumber': self.DEVICE_EXT_ID,
                'model': self.DEVICE_NAME
            }
        }
        response = requests.post(self.C8Y_BASE + '/inventory/managedObjects', headers=self.C8Y_HEADERS, data=json.dumps(device))
        DEVICE_ID = response.json()['id']
        externalId = {
            'type': 'c8y_Serial',
            'externalId': self.DEVICE_EXT_ID
        }
        response = requests.post(self.C8Y_BASE + '/identity/globalIds/' + DEVICE_ID + '/externalIds', headers=self.C8Y_HEADERS, data=json.dumps(externalId))
        return DEVICE_ID

    def updateDevice(self, update):
        response = requests.put(self.C8Y_BASE + '/inventory/managedObjects/' + str(self.DEVICE_ID), headers=self.C8Y_HEADERS, data=json.dumps(update))
        return response

    def setC8YHeaders(self, AUTH):
        self.C8Y_HEADERS = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Basic ' + base64.b64encode(AUTH.encode('utf-8')).decode('utf-8')
        }

    def connect(self):
        # -------------------------------------------
        # Perform Bootstrap
        exists = os.path.isfile('credentials.txt')

        if exists != True:
            status = 0
            while status != 201:
                device_credentials = self.getDeviceCredentials(self.DEVICE_EXT_ID)
                status = device_credentials.status_code
                if (status != 201):
                    time.sleep(4)

            C8Y_USER = device_credentials.json()['username']
            C8Y_PASSWORD = device_credentials.json()['password']
            AUTH = self.C8Y_TENANT + '/' + C8Y_USER + ':' + C8Y_PASSWORD
            self.setC8YHeaders(AUTH)
            self.DEVICE_ID = self.createDevice()

            file = open('credentials.txt', 'w+')
            file.write(self.DEVICE_ID + "\n")
            file.write(AUTH)
            file.close()

        else:
            with open('credentials.txt') as file: lines = file.read().splitlines()
            self.DEVICE_ID = lines[0]
            AUTH = lines[1]
            self.setC8YHeaders(AUTH)

        logging.info('Connected to device ID: ' + self.DEVICE_ID)
        print(AUTH)
        print(self.C8Y_HEADERS)
