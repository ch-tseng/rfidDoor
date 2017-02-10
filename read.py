#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import json
import time
import urllib.request
from libraryCH.device.lcd import ILI9341
from libraryCH.device.camera import PICamera

ImgFacePath = "/var/www/html/captured/"
urlHeadString = "http://data.sunplusit.com/Api/DoorRFIDInfo?code=83E4621643F7B2E148257244000655E3&rfid="

lcd = ILI9341(LCD_Rotate=90)
lcd.displayImg("test.jpg")

camera = PICamera()
camera.cameraResolution = (1280, 720)
#camera.takePicture()

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
lcd_LineNow = 0
lcd_lineHeight = 30
lcd_totalLine = 8  #320/30

def is_json(myjson):
    try:
        json_object = json.loads(myjson)

    except ValueError:
        return False

    return True

def lcd_Line2Pixel(lineNum):
    return lcd_lineHeight*lineNum

def lcd_nextLine():
    global lcd_LineNow
    lcd_LineNow+=1
    if(lcd_LineNow>(lcd_totalLine-1)):
        lcd.displayClear()
        lcd_LineNow = 0

def displayUser(empNo, empName, uid):
    global lcd_LineNow

    if(lcd_LineNow>0): lcd_nextLine()

    lcd.displayText("cfont1.ttf", fontSize=18, text=empNo, position=(lcd_Line2Pixel(lcd_LineNow), 110), fontColor=(253,244,6) )
    lcd.displayText("cfont1.ttf", fontSize=26, text=empName, position=(lcd_Line2Pixel(lcd_LineNow), 10) )

    lcd_nextLine()
    lcd.displayText("cfont1.ttf", fontSize=22, text=uid, position=(lcd_Line2Pixel(lcd_LineNow), 10), fontColor=(88,88,87) )

while True:
    lineRead = ser.readline()   # read a '\n' terminated line
    print (lineRead)
    lineRead = lineRead.decode('utf-8').rstrip()

    if(len(lineRead)>0):
        print(urlHeadString + lineRead)
        print('Length: {}'.format(len(lineRead)))

        webReply = urllib.request.urlopen(urlHeadString + lineRead).read()
        webReply = webReply.decode('utf-8').rstrip()
        print(webReply)

        if(is_json(webReply)==True):
            jsonReply = json.loads(webReply)

            if(len(jsonReply)>0):
                camera.takePicture("/var/www/html/rfidface/"+jsonReply[0]["EmpNo"]+str(time.time())+".jpg")

                for i in range(0, len(jsonReply)):
                    print(jsonReply[i]["EmpCName"])
                    displayUser(jsonReply[i]["EmpNo"], jsonReply[i]["EmpCName"], jsonReply[i]["Uid"])

        else:
            lcd.displayText("cfont1.ttf", fontSize=24, text=lineRead, position=(lcd_Line2Pixel(0), 10) )

ser.close()
