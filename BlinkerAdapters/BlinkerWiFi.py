try:
    import modules.urequests as requests
except ImportError:
    import requests
import ujson
from modules.simple import MQTTClient
from Blinker.BlinkerConfig import *
from Blinker.BlinkerDebug import *
from BlinkerUtility.BlinkerUtility import *

class MQTTProtocol(object):
    host = ''
    port = ''
    subtopic = ''
    pubtopic = ''
    deviceName = ''
    clientID = ''
    userName = ''
    password = ''
    uuid = ''
    msgBuf = ''
    isRead = False
    isAliRead = False
    state = CONNECTING
    isAlive = False
    isAliAlive = False
    printTime = 0
    kaTime = 0
    aliKaTime = 0
    debug = BLINKER_DEBUG
    smsTime = 0
    pushTime = 0
    wechatTime = 0
    weatherTime = 0
    aqiTime = 0

class BlinkerMQTT(MQTTProtocol):
    def checkKA(self):
        if self.isAlive is False:
            return False
        if (millis() - self.kaTime) < BLINKER_MQTT_KEEPALIVE:
            return True
        else:
            self.isAlive = False
            return False

    def checkCanPrint(self):
        if self.checkKA() is False:
            BLINKER_ERR_LOG("MQTT NOT ALIVE OR MSG LIMIT")
            return False
        if (millis() - self.printTime) >= BLINKER_MQTT_MSG_LIMIT or self.printTime == 0:
            return True
        BLINKER_ERR_LOG("MQTT NOT ALIVE OR MSG LIMIT")
        return False

    def checkSMS(self):
        if (millis() - self.smsTime) >= BLINKER_SMS_MSG_LIMIT or self.smsTime == 0:
            return True
        BLINKER_ERR_LOG("SMS MSG LIMIT")
        return False

    def checkPUSH(self):
        if (millis() - self.pushTime) >= BLINKER_PUSH_MSG_LIMIT or self.pushTime == 0:
            return True
        BLINKER_ERR_LOG("PUSH MSG LIMIT")
        return False

    def checkWECHAT(self):
        if (millis() - self.wechatTime) >= BLINKER_PUSH_MSG_LIMIT or self.wechatTime == 0:
            return True
        BLINKER_ERR_LOG("WECHAT MSG LIMIT")
        return False

    def checkWEATHER(self):
        if (millis() - self.weatherTime) >= BLINKER_WEATHER_MSG_LIMIT or self.weatherTime == 0:
            return True
        BLINKER_ERR_LOG("WEATHER MSG LIMIT")
        return False

    def checkAQI(self):
        if (millis() - self.aqiTime) >= BLINKER_AQI_MSG_LIMIT or self.aqiTime == 0:
            return True
        BLINKER_ERR_LOG("AQI MSG LIMIT")
        return False

    def delay100ms(self):
        start = millis()
        time_run = 0
        while time_run < 100:
            time_run = millis() - start

    def delay10s(self):
        start = millis()
        time_run = 0
        while time_run < 10000:
            time_run = millis() - start

    def checkAuthData(self, data):
        if data['detail'] == BLINKER_CMD_NOTFOUND:
            while True:
                BLINKER_ERR_LOG("Please make sure you have put in the right AuthKey!")
                self.delay10s()

    @classmethod
    def getInfo(cls, auth, aliType, duerType):
        host = 'https://iotdev.clz.me'
        url = '/api/v1/user/device/diy/auth?authKey=' + auth

        if aliType :
            url = url + aliType

        if duerType :
            url = url + duerType

        r = requests.get(host + url)

        data = r.json()
        cls().checkAuthData(data)
        # if cls().isDebugAll() is True:
        BLINKER_LOG_ALL('Device Auth Data: ', data)
        
        data = r.json()
        deviceName = data['detail']['deviceName']
        iotId = data['detail']['iotId']
        iotToken = data['detail']['iotToken']
        productKey = data['detail']['productKey']
        uuid = data['detail']['uuid']
        broker = data['detail']['broker']

        bmt = cls()

        BLINKER_LOG_ALL('deviceName: ', deviceName)
        BLINKER_LOG_ALL('iotId: ', iotId)
        BLINKER_LOG_ALL('iotToken: ', iotToken)
        BLINKER_LOG_ALL('productKey: ', productKey)
        BLINKER_LOG_ALL('uuid: ', uuid)
        BLINKER_LOG_ALL('broker: ', broker)
        BLINKER_LOG_ALL('host + url: ', host + url)

        if broker == 'aliyun':
            bmt.host = BLINKER_MQTT_ALIYUN_HOST
            bmt.port = BLINKER_MQTT_ALIYUN_PORT
            bmt.subtopic = '/' + productKey + '/' + deviceName + '/r'
            bmt.pubtopic = '/' + productKey + '/' + deviceName + '/s'
            bmt.clientID = deviceName
            bmt.userName = iotId

        bmt.deviceName = deviceName
        bmt.password = iotToken
        bmt.uuid = uuid

        # if bmt.isDebugAll() is True:
        BLINKER_LOG_ALL('clientID: ', bmt.clientID)
        BLINKER_LOG_ALL('userName: ', bmt.userName)
        BLINKER_LOG_ALL('password: ', bmt.password)
        BLINKER_LOG_ALL('subtopic: ', bmt.subtopic)
        BLINKER_LOG_ALL('pubtopic: ', bmt.pubtopic)

        return bmt

def on_message(topic, msg):
    BLINKER_LOG_ALL('payload: ', msg)
    data = ujson.loads(msg)

class MQTTClients():
    def __init__(self):
        self.auth = ''
        self._isClosed = False
        self.client = None
        self.bmqtt = None
        self.mProto = BlinkerMQTT()
        self.aliType = ''
        self.duerType = ''
        self.isMQTTinit = False
        self.mqttPing = 0

    def start(self, auth, aliType, duerType):
        self.auth = auth
        self.aliType = aliType
        self.duerType = duerType  

    def on_message(self, topic, msg):
        BLINKER_LOG_ALL('payload: ', msg)
        data = ujson.loads(msg)
        fromDevice = data['fromDevice']
        data = data['data']
        data = ujson.dumps(data)
        BLINKER_LOG_ALL('data: ', data)
        if fromDevice == self.bmqtt.uuid :
            self.bmqtt.msgBuf = data
            self.bmqtt.isRead = True
            self.bmqtt.isAlive = True
            self.bmqtt.kaTime = millis()
        elif fromDevice == 'AliGenie':
            self.bmqtt.msgBuf = data
            self.bmqtt.isAliRead = True
            self.bmqtt.isAliAlive = True
            self.bmqtt.aliKaTime = millis()            

    def pub(self, msg, state=False):
        if state is False:
            if self.bmqtt.checkCanPrint() is False:
                return
        payload = {'fromDevice': self.bmqtt.deviceName, 'toDevice': self.bmqtt.uuid, 'data': msg , 'deviceType': 'OwnApp'}
        payload = ujson.dumps(payload)
        # if self.bmqtt.isDebugAll() is True:
        BLINKER_LOG_ALL('Publish topic: ', self.bmqtt.pubtopic)
        BLINKER_LOG_ALL('payload: ', payload)
        self.client.publish(self.bmqtt.pubtopic, payload)
        self.bmqtt.printTime = millis()

    def aliPrint(self, msg):
        payload = {'fromDevice': self.bmqtt.deviceName, 'toDevice': 'AliGenie_r', 'data': msg , 'deviceType': 'vAssistant'}
        payload = ujson.dumps(payload)
        # if self.bmqtt.isDebugAll() is True:
        BLINKER_LOG_ALL('Publish topic: ', self.bmqtt.pubtopic)
        BLINKER_LOG_ALL('payload: ', payload)
        self.client.publish(self.bmqtt.pubtopic, payload)    

    def duerPrint(self, msg):
        payload = {'fromDevice': self.bmqtt.deviceName, 'toDevice': 'DuerOS_r', 'data': msg , 'deviceType': 'vAssistant'}
        payload = ujson.dumps(payload)
        # if self.bmqtt.isDebugAll() is True:
        BLINKER_LOG_ALL('Publish topic: ', self.bmqtt.pubtopic)
        BLINKER_LOG_ALL('payload: ', payload)
        self.client.publish(self.bmqtt.pubtopic, payload)

    def connect(self):
        if self.isMQTTinit is False :
            self.bmqtt = self.mProto.getInfo(self.auth, self.aliType, self.duerType)
            self.isMQTTinit = True
            self.client = MQTTClient(client_id = self.bmqtt.clientID, 
                server = self.bmqtt.host, port = self.bmqtt.port, 
                user = self.bmqtt.userName, password =self.bmqtt.password, 
                keepalive = 60, ssl = True)
            self.client.set_callback(self.on_message)
            self.client.connect()
            self.client.subscribe(self.bmqtt.subtopic)

            self.mqttPing = millis()
        else :
            try:
                self.client.check_msg()
                self.mProto.delay100ms()
            except Exception as error:
                self.client.disconnect()
                MQTTClients.reconnect(self)

    def reconnect(self):
        try:
            MQTTClients.register(self)

            self.client = MQTTClient(client_id = self.bmqtt.clientID, 
                server = self.bmqtt.host, port = self.bmqtt.port, 
                user = self.bmqtt.userName, password =self.bmqtt.password, 
                keepalive = 60, ssl = True)
            self.client.set_callback(self.on_message)
            self.client.connect(clean_session = True)
            self.client.subscribe(self.bmqtt.subtopic)
        except Exception as error:
            BLINKER_ERR_LOG('MQTT reconnect failed...')

    def register(self):
        self.bmqtt = self.mProto.getInfo(self.auth, self.aliType, self.duerType)