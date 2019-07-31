try:
    import modules.urequests as requests
except ImportError:
    import requests
import ujson
from network import STA_IF, WLAN
from Blinker.BlinkerConfig import *
from Blinker.BlinkerDebug import *
# from client import HTTPConnection

class Protocol():
    def __init__(self):
        self.conType = "BLINKER_WIFI"
        self.proto1 = None
        self.proto2 = None
        self.conn1 = None
        self.conn2 = None
        # self.debug = BLINKER_DEBUG

        self.msgFrom = None
        self.msgBuf = None
        self.sendBuf = ''
        self.isFormat = False
        self.autoFormatFreshTime = millis()
        self.state = CONNECTING

        self.isAvail = False
        self.isRead = False

        self.isThreadStart = False
        self.thread = None

        self.Buttons = {}
        self.Sliders = {}
        self.Toggles = {}
        self.Numbers = {}
        self.Texts = {}
        self.Datas = {}

        self.dataTime = BLINKER_DATA_FREQ_TIME
        self.dataCount = 0
        self.dataTimes = 0
        self.dataTimesLimit = 0
        self.dataStorageFunc = None

        # self.Joystick = [BLINKER_JOYSTICK_VALUE_DEFAULT, BLINKER_JOYSTICK_VALUE_DEFAULT]
        self.Joystick = {}
        self.Ahrs = [0, 0, 0, False]
        self.GPS = ["0.000000", "0.000000"]
        self.RGB = {}

        self.dataFunc = None
        self.heartbeatFunc = None        
        self.summaryFunc = None

        self.aliType = None
        self.duerType = None

        self.aliPowerSrareFunc = None
        self.aliSetColorFunc = None
        self.aliSetModeFunc = None
        self.aliSetcModeFunc = None
        self.aliSetBrightFunc = None
        self.aliRelateBrightFunc = None
        self.aliSetColorTempFunc = None
        self.aliRelateColorTempFunc = None
        self.aliQueryFunc = None

bProto = Protocol()

wlan = WLAN(STA_IF)

class BlinkerMpy:
    def mode(self, setType = 'BLINKER_WIFI'):
        if setType == "BLINKER_BLE":
            bProto.conType = setType
            return
        elif setType == "BLINKER_MQTT" or setType == "BLINKER_WIFI":
            bProto.conType = "BLINKER_MQTT"
            BLINKER_LOG('MODE: BLINKER_WIFI')

            import BlinkerAdapters.BlinkerWiFi as bMQTT

            bProto.proto1 = bMQTT
            bProto.conn1 = bProto.proto1.MQTTClients()

    def aliType(self, _type):
        if _type == 'BLINKER_ALIGENIE_LIGHT':
            bProto.aliType = '&aliType=light'
        elif _type == 'BLINKER_ALIGENIE_OUTLET':
            bProto.aliType = '&aliType=outlet'
        elif _type == 'BLINKER_ALIGENIE_MULTI_OUTLET':
            bProto.aliType = '&aliType=multi_outlet'
        elif _type == 'BLINKER_ALIGENIE_SENSOR':
            bProto.aliType = '&aliType=sensor'

    def duerType(self, _type):
        if _type == 'BLINKER_DUEROS_LIGHT':
            bProto.duerType = '&duerType=LIGHT'
        elif _type == 'BLINKER_DUEROS_OUTLET':
            bProto.duerType = '&duerType=SOCKET'
        elif _type == 'BLINKER_DUEROS_MULTI_OUTLET':
            bProto.duerType = '&duerType=MULTI_SOCKET'        
        elif _type == 'BLINKER_DUEROS_SENSOR':
            bProto.duerType = '&duerType=AIR_MONITOR'
        
    def begin(self, auth = None, ssid = None, pswd = None):
        if bProto.conType == "BLINKER_BLE":
            BLINKER_LOG('MODE: BLINKER_BLE')
        elif bProto.conType == "BLINKER_MQTT":
            BLINKER_LOG('auth: ', auth)
            wlan.active(True)
            wlan.connect(ssid, pswd)
            
            bProto.conn1.start(auth, bProto.aliType, bProto.duerType)

            time.sleep(10.0)

    def checkData(self):
        if bProto.conType == "BLINKER_BLE":
            # return
            bProto.state = bProto.proto1.bleProto.state
            if bProto.proto1.bleProto.isRead is True:
                bProto.msgBuf = bProto.proto1.bleProto.msgBuf
                bProto.isRead = True
                bProto.proto1.bleProto.isRead = False
                # BlinkerMpy.parse(self)
        elif bProto.conType == "BLINKER_MQTT":
            bProto.state = bProto.conn1.bmqtt.state
            # if bProto.proto2.wsProto.state is CONNECTED:
            #     bProto.state = bProto.proto2.wsProto.state
            if bProto.conn1.bmqtt.isRead is True:
                bProto.msgBuf = bProto.conn1.bmqtt.msgBuf
                bProto.msgFrom = "BLINKER_MQTT"
                bProto.isRead = True
                bProto.conn1.bmqtt.isRead = False
                BlinkerMpy.parse(self)
            if bProto.conn1.bmqtt.isAliRead is True:
                bProto.msgBuf = bProto.conn1.bmqtt.msgBuf
                bProto.conn1.bmqtt.isAliRead = False
                BlinkerMpy.aliParse(self)
            # if bProto.proto2.wsProto.isRead is True:
            #     bProto.msgBuf = str(bProto.proto2.wsProto.msgBuf)
            #     bProto.msgFrom = "BLINKER_WIFI"
            #     bProto.isRead = True
            #     bProto.proto2.wsProto.isRead = False
            #     BlinkerMpy.parse(self)

    def run(self):
        if wlan.isconnected():
            bProto.conn1.connect()
        else:
            BLINKER_LOG('network disconnected')
            time.sleep(2.0)        
        BlinkerMpy.checkData(self)
        BlinkerMpy.checkAutoFormat(self)


    
    def checkLength(self, data):
        if len(data) > BLINKER_MAX_SEND_SIZE:
            BLINKER_ERR_LOG('SEND DATA BYTES MAX THAN LIMIT!')
            return False
        else:
            return True

    def _print(self, data):
        if BlinkerMpy.checkLength(self, data) is False:
            return
        
        if bProto.conType == "BLINKER_BLE":
            bProto.conn1.response(data)
        # elif bProto.conType == "BLINKER_WIFI":
        #     bProto.conn1.broadcast(data)
        elif bProto.conType == "BLINKER_MQTT" and bProto.msgFrom == "BLINKER_MQTT":
            if BLINKER_CMD_NOTICE in data:
                _state = True
            elif BLINKER_CMD_STATE in data:
                _state = True
            else:
                _state = False
            bProto.conn1.pub(data, _state)
        # elif bProto.conType == "BLINKER_MQTT" and bProto.msgFrom == "BLINKER_WIFI":
        #     bProto.conn2.broadcast(data)

        # BlinkerMpy._parse(self, data)

    def print(self, key, value = None, uint = None):

        if value is None:
            if bProto.isFormat:
                return
            data = str(key)
            BlinkerMpy._print(self, data)
        else:
            key = str(key)
            # if not uint is None:
            #     value = str(value) + str(uint)
            # data = json_encode(key, value)
            # data = {}
            if bProto.isFormat == False:
                bProto.isFormat = True
                bProto.autoFormatFreshTime = millis()
            
            if (millis() - bProto.autoFormatFreshTime) < 100 :
                bProto.autoFormatFreshTime = millis()

            buffer = {}

            if bProto.sendBuf is not '' :
                buffer = ujson.loads(bProto.sendBuf)
            buffer[key] = value
            bProto.sendBuf = ujson.dumps(buffer)
            # # bProto.sendBuf[key] = value

            # # BLINKER_LOG_ALL("key: ", key, ", value: ", bProto.sendBuf[key])
            BLINKER_LOG_ALL("sendBuf: ", bProto.sendBuf)

    def checkAutoFormat(self):
        if bProto.isFormat :
            if (millis() - bProto.autoFormatFreshTime) >= 100 :
                # payload = {}
                # for key in bProto.sendBuf :
                #     BLINKER_LOG_ALL(key, ", ", bProto.sendBuf[key])
                BLINKER_LOG_ALL("auto format: ", ujson.loads(bProto.sendBuf))
                BlinkerMpy._print(self, ujson.loads(bProto.sendBuf))
                bProto.sendBuf = ''
                bProto.isFormat = False

    def connected(self):
        if bProto.state is CONNECTED:
            return True
        else:
            return False 

    def connect(self, timeout = BLINKER_STREAM_TIMEOUT):
        bProto.state = CONNECTING
        start_time = millis()
        while (millis() - start_time) < timeout:
            BlinkerMpy.run(self)
            if bProto.state is CONNECTED:
                return True
        return False

    def disconnect(self):
        bProto.state = DISCONNECTED

    def delay(self, ms):
        start = millis()
        time_run = 0
        while time_run < ms:
            BlinkerMpy.run(self)
            time_run = millis() - start

    def available(self):
        return bProto.isAvail

    def attachData(self, func):
        bProto.dataFunc = func

    def attachHeartbeat(self, func):
        bProto.heartbeatFunc = func

    def attachSummary(self, func):
        bProto.summaryFunc = func

    def readString(self):
        bProto.isRead = False
        bProto.isAvail = False
        return bProto.msgBuf

    def times(self):
        return millis()

    def aliParse(self):
        data = bProto.msgBuf
        if not data:
            return
        try:
            data = ujson.loads(data)
            BLINKER_LOG(data)
            # if data.has_key('set'):
            if 'set' in data.keys():
                data = data['set']
                for key, value in data.items():
                    if key == 'pState':
                        if bProto.aliPowerSrareFunc:
                            # if data.has_key('num'):
                            if 'num' in data.keys():
                                bProto.aliPowerSrareFunc(value, data['num'])
                            else :
                                bProto.aliPowerSrareFunc(value)
                    elif key == 'clr':
                        if bProto.aliSetColorFunc:
                            bProto.aliSetColorFunc(value)
                    elif key == 'bright':
                        if bProto.aliSetBrightFunc:
                            bProto.aliSetBrightFunc(value)
                    elif key == 'upBright':
                        if bProto.aliRelateBrightFunc:
                            bProto.aliRelateBrightFunc(value)
                    elif key == 'downBright':
                        if bProto.aliRelateBrightFunc:
                            bProto.aliRelateBrightFunc(value)
                    elif key == 'colTemp':
                        if bProto.aliSetColorTempFunc:
                            bProto.aliSetColorTempFunc(value)
                    elif key == 'upColTemp':
                        if bProto.aliRelateColorTempFunc:
                            bProto.aliRelateColorTempFunc(value)
                    elif key == 'downColTemp':
                        if bProto.aliRelateColorTempFunc:
                            bProto.aliRelateColorTempFunc(value)
                    elif key == 'mode':
                        if bProto.aliSetModeFunc:
                            bProto.aliSetModeFunc(value)
                    elif key == 'cMode':
                        if bProto.aliSetcModeFunc:
                            bProto.aliSetcModeFunc(value)
            # elif data.has_key('get'):
            elif 'get' in data.keys():
                data = data['get']
                if data == 'state':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_ALL_NUMBER)
                elif data == 'pState':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_POWERSTATE_NUMBER)
                elif data == 'clr':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_COLOR_NUMBER)
                elif data == 'colTemp':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_COLORTEMP_NUMBER)
                elif data == 'bright':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_BRIGHTNESS_NUMBER)
                elif data == 'temp':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_TEMP_NUMBER)
                elif data == 'humi':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_HUMI_NUMBER)
                elif data == 'pm25':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_PM25_NUMBER)
                elif data == 'pState':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_POWERSTATE_NUMBER)
                elif data == 'mode':
                    if bProto.aliQueryFunc:
                        bProto.aliQueryFunc(BLINKER_CMD_QUERY_MODE_NUMBER)

        except ValueError:
            pass
        except TypeError:
            pass
        finally:
            pass



    def parse(self):
        data = bProto.msgBuf
        if not data:
            return
        try:
            data = ujson.loads(data)
            BLINKER_LOG(data)
            # if not isinstance(data, dict):
            #     raise TypeError()
            for key, value in data.items():
                if key in bProto.Buttons:
                    bProto.isRead = False
                    bProto.Buttons[key].func(data[key])
                elif key in bProto.Sliders:
                    bProto.isRead = False
                    bProto.Sliders[key].func(data[key])
                # elif key in bProto.Toggles:
                #     bProto.isRead = False
                #     bProto.Toggles[key].func(data[key])
                elif key in bProto.RGB:
                    bProto.isRead = False
                    BLINKER_LOG(bProto.RGB[key])
                    bProto.RGB[key].func(data[key][R], data[key][G], data[key][B], data[key][BR])
                elif key in bProto.Joystick:
                    bProto.isRead = False
                    bProto.Joystick[key].func(data[key][J_Xaxis], data[key][J_Yaxis])
                elif key == BLINKER_CMD_AHRS:
                    # bProto.isAvail = False
                    bProto.isRead = False
                    bProto.Ahrs[Yaw] = data[key][Yaw]
                    bProto.Ahrs[Pitch] = data[key][Pitch]
                    bProto.Ahrs[Roll] = data[key][Roll]
                    bProto.Ahrs[AHRS_state] = True
                    # BLINKER_LOG(bProto.Ahrs)
                elif key == BLINKER_CMD_GPS:
                    bProto.isRead = False
                    bProto.GPS[LONG] = str(data[key][LONG])
                    bProto.GPS[LAT] = str(data[key][LAT])

                elif key == BLINKER_CMD_GET and data[key] == BLINKER_CMD_VERSION:
                    bProto.isRead = False
                    BlinkerMpy.print(self, BLINKER_CMD_VERSION, BLINKER_VERSION)

                elif key == BLINKER_CMD_GET and data[key] == BLINKER_CMD_STATE:
                    bProto.isRead = False
                    BlinkerMpy.heartbeat(self)
        
        except ValueError:
            pass
        except TypeError:
            pass
        finally:
            if bProto.isRead:
                # bProto.isAvail = 
                if bProto.dataFunc :
                    bProto.dataFunc(data)
                # bProto.isAvail = False

    def heartbeat(self):
        if bProto.conType == 'BLINKER_MQTT':
            # beginFormat()
            BlinkerMpy.print(self, BLINKER_CMD_STATE, BLINKER_CMD_ONLINE)
            if bProto.heartbeatFunc :
                bProto.heartbeatFunc()
            if bProto.summaryFunc :
                bProto.summaryFunc()
            # stateData()
            # if endFormat() is False:
            #     print(BLINKER_CMD_STATE, BLINKER_CMD_ONLINE)
        else:
            # beginFormat()
            BlinkerMpy.print(self, BLINKER_CMD_STATE, BLINKER_CMD_CONNECTED)
            if bProto.heartbeatFunc :
                bProto.heartbeatFunc()
            if bProto.summaryFunc :
                bProto.summaryFunc()

    def attachAliGenieSetPowerState(self, _func):
        bProto.aliPowerSrareFunc = _func
    
    def attachAliGenieSetColor(self, _func):
        bProto.aliSetColorFunc = _func

    def attachAliGenieSetMode(self, _func):
        bProto.aliSetModeFunc = _func

    def attachAliGenieSetcMode(self, _func):
        bProto.aliSetcModeFunc = _func

    def attachAliGenieSetBrightness(self, _func):
        bProto.aliSetBrightFunc = _func

    def attachAliGenieRelativeBrightness(self, _func):
        bProto.aliRelateBrightFunc = _func

    def attachAliGenieSetColorTemperature(self, _func):
        bProto.aliSetColorTempFunc = _func

    def attachAliGenieRelativeColorTemperature(self, _func):
        bProto.aliRelateColorTempFunc = _func

    def attachAliGenieQuery(self, _func):
        bProto.aliQueryFunc = _func

    def aliPrint(self, data):
        bProto.conn1.aliPrint(data)

Blinker = BlinkerMpy()

class BlinkerButton(object):
    """ """

    def __init__(self, name, func=None):
        self.name = name
        self.func = func
        self._icon = ""
        self.iconClr = ""
        self._content = ""
        self._text = ""
        self._text1 = ""
        self.textClr = ""
        self.buttonData = {}

        bProto.Buttons[name] = self

    def icon(self, _icon):
        self._icon = _icon

    def color(self, _clr):
        self.iconClr = _clr

    def content(self, _con):
        self._content = str(_con)

    def text(self, _text1, _text2=None):
        self._text = str(_text1)
        if _text2:
            self._text1 = str(_text2)

    def textColor(self, _clr):
        self.textClr = _clr

    def attach(self, func):
        self.func = func

    def print(self, state=None):

        if state :
            self.buttonData[BLINKER_CMD_SWITCH] = state
        if self._icon:
            self.buttonData[BLINKER_CMD_ICON] = self._icon
        if self.iconClr:
            self.buttonData[BLINKER_CMD_COLOR] = self.iconClr
        if self._content:
            self.buttonData[BLINKER_CMD_CONNECTED] = self._content
        if self._text:
            self.buttonData[BLINKER_CMD_TEXT] = self._text
        if self._text1:
            self.buttonData[BLINKER_CMD_TEXT1] = self._text1
        if self.textClr:
            self.buttonData[BLINKER_CMD_TEXTCOLOR] = self.textClr

        if len(self.buttonData) :
            # data = json.dumps(self.buttonData)
            # data = {self.name: self.buttonData}
            # Blinker._print(data)
            Blinker.print(self.name, self.buttonData)

            self.buttonData.clear()

            self._icon = ""
            self.iconClr = ""
            self._content = ""
            self._text = ""
            self._text1 = ""
            self.textClr = ""


class BlinkerNumber(object):
    """ """

    def __init__(self, name):
        self.name = name
        self._icon = ""
        self._color = ""
        self._unit = ""
        self._text = ""
        self.numberData = {}

        bProto.Numbers[name] = self

    def icon(self, _icon):
        self._icon = _icon

    def color(self, _clr):
        self._color = _clr

    def unit(self, _unit):
        self._unit = _unit
    
    def text(self, _text):
        self._text = _text

    def print(self, value = None):
        if value:
            self.numberData[BLINKER_CMD_VALUE] = value
        if self._icon:
            self.numberData[BLINKER_CMD_ICON] = self._icon
        if self._color:
            self.numberData[BLINKER_CMD_COLOR] = self._color
        if self._unit:
            self.numberData[BLINKER_CMD_UNIT] = self._unit
        if self._text:
            self.numberData[BLINKER_CMD_TEXT] = self._text

        if len(self.numberData) :
            # data = json.dumps(self.numberData)
            # data = {self.name: self.numberData}
            # Blinker._print(data)
            Blinker.print(self.name, self.numberData)

            self.numberData.clear()

            self._icon = ""
            self._color = ""
            self._unit = ""
            self._text = ""


class BlinkerRGB(object):
    """ """

    def __init__(self, name, func=None):
        self.name = name
        self.func = func
        self.rgbbrightness = 0
        self.rgbData = []
        self.registered = False

        bProto.RGB[name] = self

    def attach(self, func):
        self.func = func

    def brightness(self, _bright):
        self.rgbbrightness = _bright

    def print(self, r, g, b, _bright=None):
        self.rgbData.append(r)
        self.rgbData.append(g)
        self.rgbData.append(b)
        if _bright is None:
            self.rgbData.append(self.rgbbrightness)
        else:
            self.rgbData.append(_bright)
        
        # _print(self.rgbData)
        # data = {self.name: self.rgbData}
        # Blinker._print(data)
        Blinker.print(self.name, self.rgbData)


class BlinkerSlider(object):
    """ """

    def __init__(self, name, func=None):
        self.name = name
        self.func = func
        self.textClr = ""
        self.sliderData = {}

        bProto.Sliders[name] = self

    def attach(self, func):
        self.func = func

    def color(self, _clr):
        self.textClr = _clr

    def print(self, value):
        self.sliderData[BLINKER_CMD_VALUE] = value
        if self.textClr:
            self.sliderData[BLINKER_CMD_COLOR] = self.textClr

        # data = json.dumps(self.sliderData)
        # data = {self.name: self.sliderData}
        # Blinker._print(data)
        Blinker.print(self.name, self.sliderData)


class BlinkerText(object):
    """ """

    def __init__(self, name):
        self.name = name
        self.textData = {}

        bProto.Texts[name] = self

    def print(self, text1, text2=None):
        self.textData[BLINKER_CMD_TEXT] = text1
        if text2:
            self.textData[BLINKER_CMD_TEXT1] = text2

        # data = json.dumps(self.textData)        
        # data = {self.name: self.textData}
        # Blinker._print(data)
        Blinker.print(self.name, self.textData)


class BlinkerJoystick(object):
    """ """

    def __init__(self, name, func=None):
        self.name = name
        self.func = func

        bProto.Joystick[name] = self

    def attach(self, _func):
        self.func = _func


class BlinkerSwitch(object):
    """ """

    def __init__(self, name=BLINKER_CMD_BUILTIN_SWITCH, func=None):
        self.name = name
        self.func = func

        bProto.Toggles[name] = self

    def attach(self, _func):
        self.func = _func

    def print(self, _state):
        Blinker.print(self.name, _state)

class BLINKERA_LIGENIE():
    def __init__(self):
        self.payload = {}

    def attachPowerState(self, _func):
        Blinker.attachAliGenieSetPowerState(_func)

    def attachColor(self, _func):
        Blinker.attachAliGenieSetColor(_func)

    def attachMode(self, _func):
        Blinker.attachAliGenieSetMode(_func)

    def attachCancelMode(self, _func):
        Blinker.attachAliGenieSetcMode(_func)
    
    def attachBrightness(self, _func):
        Blinker.attachAliGenieSetBrightness(_func)

    def attachRelativeBrightness(self, _func):
        Blinker.attachAliGenieRelativeBrightness(_func)

    def attachColorTemperature(self, _func):
        Blinker.attachAliGenieSetColorTemperature(_func)

    def attachRelativeColorTemperature(self, _func):
        Blinker.attachAliGenieRelativeColorTemperature(_func)

    def attachQuery(self, _func):
        Blinker.attachAliGenieQuery(_func)

    def powerState(self, state, num = None):
        self.payload['pState'] = state
        if num :
            self.payload['num'] = num

    def color(self, clr):
        self.payload['clr'] = clr

    def mode(self, md):
        self.payload['mode'] = md

    def colorTemp(self, clrTemp):
        self.payload['colTemp'] = clrTemp

    def brightness(self, bright):
        self.payload['bright'] = bright

    def temp(self, tem):
        self.payload['temp'] = tem

    def humi(self, hum):
        self.payload['humi'] = hum

    def pm25(self, pm):
        self.payload['pm25'] = pm

    def print(self):
        BLINKER_LOG_ALL(self.payload)
        Blinker.aliPrint(self.payload)
        self.payload.clear()

BlinkerAliGenie = BLINKERA_LIGENIE()

BUILTIN_SWITCH = BlinkerSwitch()