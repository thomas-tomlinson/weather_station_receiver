# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)

import network
import time 
import json

def do_connect(ssid, password):
    #network.hostname('weather-receive')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

wifi_config = {}
# try to open a config file for wifi
try:
    f = open('wifi.json', 'r')
    contents = f.read()
    f.close()
    configf = json.loads(contents)
    if 'ssid' in configf.keys() and 'password' in configf.keys():
        wifi_config['ssid']  = configf['ssid']
        wifi_config['password']  = configf['password']
        wifi_config['valid'] = True
except:
    # blanket catchall, run in AP mode
    wifi_config['valid'] = False

network.hostname('weather-receive')
if wifi_config['valid'] is True:
    do_connect(wifi_config['ssid'], wifi_config['password'])

import webrepl
webrepl.start()

