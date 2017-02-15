#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import json
import time
import datetime
import urllib.request
import logging
import os
import random
from libraryCH.device.lcd import ILI9341
import paho.mqtt.client as mqtt

#這台樹莓除了作為接收RFID, 是否要啟用相機功能
localCameraEnabled = False
#啟用的話, 儲存拍攝相片的位置
ImgFacePath = "/var/www/html/captured/"

#RFID TAG資訊要傳到何處? 下方為使用RESTFUL
urlHeadString = "http://data.sunplusit.com/Api/DoorRFIDInfo?code=83E4621643F7B2E148257244000655E3&rfid="

#LCD顯示設定
lcd = ILI9341(LCD_size_w=240, LCD_size_h=320, LCD_Rotate=90)

#開機及螢幕保護畫面
screenSaverDelay = 30  #刷卡顯示, 幾秒後回到螢幕保護畫面
lcd.displayImg("rfidbg.jpg")


#-----------------------------------------------------------------------------------------------------
#下方設定比較不需要變動
#-----------------------------------------------------------------------------------------------------

#相機設定
if(localCameraEnabled==True):
    from libraryCH.device.camera import PICamera
    camera = PICamera()
    camera.CameraConfig(rotation=180)  #相機旋轉角度
    camera.cameraResolution(resolution=(1280, 720))   #拍攝的相片尺寸

#從USB接收RFID 訊息
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

#LCD設定
lcd_LineNow = 0
lcd_lineHeight = 30  #行的高度
lcd_totalLine = 8  # LCD的行數 (320/30=8)
screenSaverNow = False

#上次讀取到TAG的內容和時間
lastUIDRead = ""
lastTimeRead = time.time()

#MQTT
ChannelPublish = "Door-camera"
MQTTuser = "chtseng"
MQTTpwd = "chtseng"
MQTTaddress = "akai-chen-pc3.sunplusit.com.tw"
MQTTport = 1883
MQTTtimeout = 60

#logging記錄
logger = logging.getLogger('msg')
hdlr = logging.FileHandler('/home/pi/rfid/msg.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

#判斷是否為JSON格式
def is_json(myjson):
    try:
        json_object = json.loads(myjson)

    except ValueError:
        return False

    return True

#將行數轉為pixels
def lcd_Line2Pixel(lineNum):
    return lcd_lineHeight*lineNum

#LCD移到下一行, 若超過設定則清螢幕並回到第0行
def lcd_nextLine():
    global lcd_LineNow
    lcd_LineNow+=1
    if(lcd_LineNow>(lcd_totalLine-1)):
        lcd.displayClear()
        lcd_LineNow = 0

#LCD顯示刷卡內容
def displayUser(empNo, empName, uid):
    global lcd_LineNow

    st = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M')
    if(lcd_LineNow>0): lcd_nextLine()

    lcd.displayText("cfont1.ttf", fontSize=20, text=st, position=(lcd_Line2Pixel(lcd_LineNow), 180), fontColor=(253,244,6) )
    lcd.displayText("cfont1.ttf", fontSize=20, text=empNo, position=(lcd_Line2Pixel(lcd_LineNow), 110) )
    lcd.displayText("cfont1.ttf", fontSize=26, text=empName, position=(lcd_Line2Pixel(lcd_LineNow), 10) )

    lcd_nextLine()
    lcd.displayText("cfont1.ttf", fontSize=22, text=uid, position=(lcd_Line2Pixel(lcd_LineNow), 10), fontColor=(88,88,87) )

def speakWelcome():
    dt = list(time.localtime())
    nowHour = dt[3]
    nowMinute = dt[4]

    mp3Number = str(random.randint(1, 3))

    if(nowHour<10 and nowHour>5):
        os.system('omxplayer --no-osd voice/gowork' + mp3Number + '.mp3')
    if(nowHour<21 and nowHour>17):
        os.system('omxplayer --no-osd voice/afterwork' + mp3Number + '.mp3')

# MQTT___________________________________________________________________________
def on_connect(mosq, obj, rc):
    logger.info('MQTT Connected.')
    print("Connected: " + str(rc))

def on_message(mosq, obj, msg):
    print("MQTT message received.")

def on_publish(mosq, obj, mid):
    logger.info("Published to MQTT broker")
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mosq, obj, level, string):
    print(string)

mqttc = mqtt.Client()
# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe
# Connect
mqttc.username_pw_set(MQTTuser, MQTTpwd)
#mqttc.connect(MQTTaddress, MQTTport, MQTTtimeout)

#-------------------------------------------------------------------------

mqttc.publish(ChannelPublish, 13545)

while True:
    lineRead = ser.readline()   # read a '\n' terminated line
    lineRead = lineRead.decode('utf-8').rstrip()

    if(len(lineRead)>0):
        print(urlHeadString + lineRead)
        print('Length: {}'.format(len(lineRead)))
        logger.info("Arduino: " + lineRead)

        webReply = urllib.request.urlopen(urlHeadString + lineRead).read()
        webReply = webReply.decode('utf-8').rstrip()
        logger.info('webReply: {}'.format(webReply))
        print(webReply)

        if(is_json(webReply)==True):
            jsonReply = json.loads(webReply)
            screenSaverNow = False

            if(len(jsonReply)>0):
                print("TEST:")
                print(jsonReply[0]["EmpNo"])
                mqttc.connect(MQTTaddress, MQTTport, MQTTtimeout)
                #mqttc.publish(ChannelPublish, "TEST MQTT")
                mqttc.publish(ChannelPublish, jsonReply[0]["EmpNo"])

                for i in range(0, len(jsonReply)):
                    logger.info('EmpCName:'+jsonReply[i]["EmpCName"])
                    logger.info('Uid:'+jsonReply[i]["Uid"])

                    if(localCameraEnabled==True):
                        camera.takePicture("/var/www/html/rfidface/"+jsonReply[0]["EmpNo"]+str(time.time())+".jpg")

                    if ((jsonReply[i]["Uid"] not in lastUIDRead) or (time.time()-lastTimeRead>60)):
                        print("Display on LCD screen.")
                        logger.info('Display on screen and speak.')
                        displayUser(jsonReply[i]["EmpNo"], jsonReply[i]["EmpCName"], jsonReply[i]["Uid"])

                        if (jsonReply[i]["TagType"]=="E"):
                            speakWelcome()
                        elif (jsonReply[i]["TagType"]=="A"):
                            os.system('omxplayer --no-osd voice/warning1.mp3')

                    logger.info('-------------------------------------------------')

                    if i==0: lastUIDRead=""
                    lastUIDRead += ","+jsonReply[i]["Uid"]
                    lastTimeRead = time.time()
                    

            else:
                lcd.displayText("cfont1.ttf", fontSize=24, text=lineRead, position=(lcd_Line2Pixel(0), 10) )
                logger.info('Unknow ID: ' + lineRead)
                lastTimeRead = time.time()

    print(time.time()-lastTimeRead)  

    if((time.time()-lastTimeRead)>screenSaverDelay and screenSaverNow==False):
        print("Display screen saveer.")
        logger.info("Display screen saveer.")
        lcd.displayImg("rfidbg.jpg")
        screenSaverNow = True

ser.close()
