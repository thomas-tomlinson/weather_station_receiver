from machine import Pin, UART, I2C
import bme280_float as bme280
import json
import time
import asyncio
from microdot import Microdot
from microdot.websocket import with_websocket
import ntptime
import network
import esp
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
    decoded = unpack_data(payload)
    if decoded is None:
        print('unpack error of payload: {}'.format(payload))
        return None
    print("raw packed: {}".format(decoded))
    # convert to final values.  mostly metric to US but also wind and rain to real units
    decoded['rainbuckets'] = process_rain_buckets(decoded['rainbuckets'])
    decoded['avg_wind'] = process_anemometer(decoded['avg_wind'])
    decoded['gust_wind'] = process_anemometer(decoded['gust_wind'])
    decoded['temp'] = c_to_f(decoded['temp'])
    decoded['pressure'] = pascal_to_inhg(decoded['pressure'])
    decoded['wind_dir'] = reverse_wind_dir(decoded['wind_dir'])
    print("processed packet: {}".format(decoded))
    return decoded

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
    #anemometer_factor = 3.95 # round 85 mm cones
    #mmps = (2 * 3.14 * count * 85 * anemometer_factor)
    #anemometer_factor = 4.995 # oval 58mm 
    #mmps = (2 * 3.14 * count * 58 * anemometer_factor)
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
    sreader = asyncio.StreamReader(uart2)
    while True: 
        readbuf = await sreader.read(33)
        remote_data = processPayload(readbuf)

        if remote_data is None:
            continue

        update_weather_data(remote_data)
        event.set()
        asyncio.create_task(flash_led()) # should be in update_weather_data

        #    currentWeatherData['remote'] = processedData
        #    currentWeatherData['local'] = read_bme280()
        #    # flash the status LED to indicate we received good data
        #    print(currentWeatherData)
        #    asyncio.create_task(flash_led())

def update_weather_data(remote_data):
    global currentWeatherData
    currentWeatherData['remote'] = remote_data
    currentWeatherData['local'] = read_bme280()
    currentWeatherData['recordtime'] = iso8601()

def retrieve_weather_data(format=None):
    global currentWeatherData
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
    wdata = retrieve_weather_data()
    wdata['requesttime'] = iso8601()
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
main()
