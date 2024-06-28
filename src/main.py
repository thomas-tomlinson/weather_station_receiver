from machine import Pin, UART, I2C
import bme280_float as bme280
import json
import time
import asyncio
import ntptime
import esp
import umsgpack
from microdot import Microdot
from microdot.websocket import with_websocket
from struct import unpack

app = Microdot()
currentWeatherData = {}
uart2 = UART(2, baudrate=9600, tx=17, rx=16)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
bme = bme280.BME280(i2c=i2c)
event = asyncio.Event()

esp.osdebug(True)

def iso8601():
    mytime = time.gmtime()
    iso8601 = str("{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}Z".format(mytime[0], mytime[1], mytime[2], mytime[3], mytime[4], mytime[5]))
    return iso8601

def processPayload(payload):
    decoded = {}
    actual_data = verify_payload(payload)
    if actual_data is None:
        print('data failed checksum.  raw data: {}'.format(actual_data))
        return None
    else:
        decoded = actual_data
    print("decoded data: {}".format(decoded))
    # convert to final values.  mostly metric to US but also wind and rain to real units
    #decoded['rainbuckets'] = process_rain_buckets(decoded['rainbuckets'])
    decoded = update_value(decoded, 'rainbuckets', process_rain_buckets)
    decoded = update_value(decoded, 'rainbuckets_last24', process_rain_buckets)
    #decoded['avg_wind'] = process_anemometer(decoded['avg_wind'])
    decoded = update_value(decoded, 'avg_wind', process_anemometer)
    #decoded['gust_wind'] = process_anemometer(decoded['gust_wind'])
    decoded = update_value(decoded, 'gust_wind', process_anemometer)
    #decoded['temp'] = c_to_f(decoded['temp'])
    decoded = update_value(decoded, 'temp', c_to_f)
    #decoded['pressure'] = pascal_to_inhg(decoded['pressure'])
    decoded = update_value(decoded, 'pressure', pascal_to_inhg)
    #decoded['wind_dir'] = reverse_wind_dir(decoded['wind_dir'])
    decoded = update_value(decoded, 'wind_dir', reverse_wind_dir)
    print("processed packet: {}".format(decoded))
    return decoded

def update_value(dict, value, method):
    if value in dict.keys():
        dict[value] = method(dict[value])
        return dict

def verify_payload(bytes):
    returndata = {}
    #have to peel off last two bytes
    checksum = bytes[-4:]
    #print("checksum: {}, type: {}".format(checksum, type(checksum)))
    checksum1, checksum2 = unpack(">hh", checksum)
    data = bytes[0:0-4:]
    datasum = sum(data)
    data1 = int(datasum // 256)
    data2 = int(datasum % 256)
    #print("checksum1: {}, data1: {}".format(checksum1, data1))
    #print("checksum2: {}, data2: {}".format(checksum2, data2))
    if checksum1 == data1 and checksum2 == data2:
        #checksum verified
        unpacked_data = umsgpack.loads(data)
        #return True, unpacked_data
        pass
    else:
        return None
    if type(unpacked_data) == 'dict':
        #returndata = unpacked_data
        return unpacked_data
    else:
        return None

def reverse_wind_dir(winddir):
    # the as5600 is now upside down, which means the values other than 0  and 180 are wrong.
    if winddir > 0 and winddir < 180:
        winddir = (360 - winddir)
    elif winddir > 180 and winddir < 360:
        winddir = (winddir - 180)

    return winddir

def process_rain_buckets(count):
    # 115.3 pulses for is 30mm.  0.26mm / pulse
    # 30 mm = 1.18inches. 1.18 / 115.3 = 0.01 inches a pulse 
    total_inches = (count * 0.01)
    return total_inches

def process_anemometer(count):
    # anemometer factor 
    anemometer_factor = 5.123 # cones with 5mm lip, 79mm
    mmps = (2 * 3.14 * count * 79 * anemometer_factor)
    mps = (mmps / 1000)
    mph = (mps * 2.237)  
    return mph

def c_to_f(temp):
    f = 32 + (temp * 9/5)
    return f

def pascal_to_inhg(pascal):
    inhg = (pascal / 3386) 
    return inhg

async def flash_led():
    led_pin = Pin(23, Pin.OUT)
    led_pin.on()
    await asyncio.sleep_ms(500)
    led_pin.off()

async def uart_listener():
    sreader = asyncio.StreamReader(uart2)
    while True: 
        readbuf = await umsgpack.aload(sreader)
        remote_data = processPayload(readbuf)

        if remote_data is None:
            continue

        update_weather_data(remote_data)
        event.set()
        asyncio.create_task(flash_led()) # should be in update_weather_data

def update_weather_data(remote_data):
    global currentWeatherData
    currentWeatherData['remote'] = remote_data
    currentWeatherData['local'] = read_bme280()
    currentWeatherData['recordtime'] = iso8601()

def retrieve_weather_data(format=None):
    global currentWeatherData
    currentWeatherData['requesttime'] = iso8601()
    if format == "json":
        return json.dumps(currentWeatherData)        
    else:
        return currentWeatherData


def read_bme280():
    dict = {}
    rawread = bme.read_compensated_data()
    dict['temp'] = c_to_f(rawread[0])
    dict['pressure'] = pascal_to_inhg(rawread[1])
    dict['humidity'] = rawread[2]
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
    wdata = {}
    wdata = retrieve_weather_data()
    return wdata

@app.route('/weather_stream')
@with_websocket
async def weather_stream(request, ws):
        while True:
            await event.wait() 
            wdata = retrieve_weather_data(format='json')
            await ws.send(wdata)
            event.clear()

async def main():
    config_hc12()
    asyncio.create_task(uart_listener())
    await app.start_server()

# ensure that time is set
while True:
    try:
        ntptime.settime()
        break
    except OSError:
        print("couldn't sync ntp, waiting 2 seconds")
        time.sleep(2)

asyncio.run(main())
