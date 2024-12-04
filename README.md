# Compling the frozen base image
The base image of micropython has microdot, umsgpack and the bme280_float modules frozen into.  Here's the steps to make a generic ESP32 port image.
1. have a functional esp-idf installation (follow the directions in the ESP32 micropython directory).  i did this in a conda env named "micropython".  Dont' forget to activate it before the next step
2. source the esp-idf exports (`source ~/src/esp-idf/export.sh`).  Remember, be in the esp-idf python environment.
3. cd into the micropython ports/esp32 directory.
4. build micropyton with the following command (`make FROZEN_MANIFEST=/Users/toto/src/weather_station_receiver/manifest.py`).  I couldn't get a relative path using ~/src to work for some reason.  Adjust to the checkout of this repo as needed.
5. copy the firmware to the esp32 with the provied command.  it will look something like this `python -m esptool --chip esp32 -b 460800 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_size 4MB --flash_freq 40m 0x1000 build-ESP32_GENERIC/bootloader/bootloader.bin 0x8000 build-ESP32_GENERIC/partition_table/partition-table.bin 0x10000 build-ESP32_GENERIC/micropython.bin`

# completing the installation
1.  copy the `boot.py` and `main.py` to the root of the esp32 device.
2.  create a file named `wifi.json` with the following forward for your local wireless network.  
```
 {"ssid": "name_of_your_ssid", "password": "password_to_your_wireless_ssid_network"}
 ```
 3.  copy the `wifi.json` to the root of the esp32 device.

