from machine import Pin, UART, I2C
import bme280_float as bme280
import json
import time
import asyncio
import binascii
from microdot import Microdot
import ntptime
import network
import esp
from struct import unpack

app = Microdot()
#currentWeatherData = {}
## hc-12 radio setup
#uart2 = UART(2, baudrate=9600, tx=17, rx=16)
#i2c = I2C(0, scl=Pin(22), sda=Pin(21))
#bme = bme280.BME280(i2c=i2c)
esp.osdebug(True)
#app = Microdot()
def iso8601():
    mytime = time.gmtime()
    iso8601 = str("{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}Z".format(mytime[0], mytime[1], mytime[2], mytime[3], mytime[4], mytime[5]))
    return iso8601

def processPayload(payload):
    filtered_data = payload
    #filtered_data = payload.replace(b'\xff', b'')
    #if len(filtered_data) == 0:
        # empty data, most likely from noise on the radio
    #    return None

    #try:
        #decoded = binascii.a2b_base64(filtered_data)
    decoded = unpack_data(filtered_data)
    if decoded is None:
        print('unpack error of payload: {}'.format(filtered_data))
        return None

    #weather_data = json.loads(decoded)
    weather_data = decoded
        
    #except ValueError as e:
    #    print('decode error: ', e, 'payload: ', filtered_data)
    #    return None

    #mytime = time.gmtime()
    #iso8601 = str("{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}Z".format(mytime[0], mytime[1], mytime[2], mytime[3], mytime[4], mytime[5]))
    weather_data['recordtime'] = iso8601()
    #print("weather_data payload: {}".format(weather_data))
    return weather_data

def unpack_data(payload):
    try:
        unpacked = unpack(">LfHHfffffs", payload)
    except Exception as e:
        print('unpack error of {}'.format(e))
        return None
    
    dict = {}
    dict['timemark'] = unpacked[0]
    dict['battery'] = unpacked[1]
    dict['rainbuckets'] = unpacked[2]
    dict['wind_dir'] = unpacked[3]
    dict['avg_wind'] = unpacked[4]
    dict['gust_wind'] = unpacked[5]
    dict['temp'] = unpacked[6]
    dict['humidity'] = unpacked[7]
    dict['pressure'] = unpacked[8]

    return dict

async def flash_led():
    led_pin = Pin(23, Pin.OUT)
    led_pin.on()
    await asyncio.sleep_ms(500)
    led_pin.off()

async def uart_listener():
    global currentWeatherData
    sreader = asyncio.StreamReader(uart2)
    while True: 
        #await asyncio.sleep(1)

        #if uart2.any() > 0:
        #    readbuf = b''
            #stopCharReached = False
            # we need to read up to the first new line, then process
            #while stopCharReached is False:
            #    await asyncio.sleep(0.1)
            #    char = uart2.read(1)
            #    if char is None:
            #        continue
            #    if char == b'\n':
            #        #break character reached, end this
            #        stopCharReached = True
            #    else:
            #        readbuf = readbuf + char
            #readbuf = uart2.readline()
            #processedData = processPayload(readbuf)
        #readbuf = await sreader.readline()
        readbuf = await sreader.read(33)
        processedData = processPayload(readbuf)

        if processedData is not None:
            currentWeatherData['remote'] = processedData
            currentWeatherData['local'] = read_bme280()
            # flash the status LED to indicate we received good data
            print(currentWeatherData)
            asyncio.create_task(flash_led())

def read_bme280():
    dict = {}
    rawread = bme.values
    dict['temp'] = rawread[0]
    dict['pressure'] = rawread[1]
    dict['humidity'] = rawread[2]
    dict['recordtime'] = iso8601()
    return dict

def config_hc12():
    # init the HC-12 
    set_pin = Pin(26, Pin.OUT)
    set_pin.off()
    time.sleep_ms(200)
    uart2.write('AT')
    time.sleep_ms(200)
    trash = uart2.read()
    uart2.flush()
    set_pin.on()
    time.sleep_ms(200)
    # exit of config mode back to normal operation

@app.route('/')
async def index(request):
    global currentWeatherData
    currentWeatherData['requesttime'] = iso8601()
    return currentWeatherData

async def main():
    asyncio.create_task(uart_listener())
    await app.start_server()
    #while True:
    #    await asyncio.sleep_ms(100)

currentWeatherData = {}
# hc-12 radio setup
uart2 = UART(2, baudrate=9600, tx=17, rx=16)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
bme = bme280.BME280(i2c=i2c)

config_hc12()

# try to get the time
while True:
    try:
        ntptime.settime()
        break
    except OSError:
        print("couldn't sync ntp, waiting 2 seconds")
        time.sleep(2)
# hc12 setup

asyncio.run(main())
main()