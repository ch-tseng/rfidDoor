#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import urllib.request
from libraryCH.device.lcd import ILI9341

lcd = ILI9341()
lcd.displayImg("/home/pi/rfid/test.jpg")

urlHeadString = "http://data.sunplusit.com/Api/DoorRFIDInfo?code=83E4621643F7B2E148257244000655E3&rfid="

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
while True:
    lineRead = ser.readline()   # read a '\n' terminated line
    lineRead = lineRead.decode('utf-8').rstrip()

    if(len(lineRead)>0):
        print(urlHeadString + lineRead)
        print('Length: {}'.format(len(lineRead)))

        webReply = urllib.request.urlopen(urlHeadString + lineRead).read()
        print(webReply.decode('utf-8').rstrip())

ser.close()
