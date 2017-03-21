#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import json
import time
import datetime
import urllib.request
import logging
import os,sys
import random
from libraryCH.device.lcd import ILI9341
import paho.mqtt.client as mqtt

debugPrint = False

#幾秒內重複的TAG不算.
tagRepeatSeconds = 30

#這台樹莓除了作為接收RFID, 是否要啟用相機功能
localCameraEnabled = True
cameraType = 1  # 0 --> PICamera . 1 --> Web Camera

#儲放相片的主目錄
picturesPath = "/var/www/html/rfidface/"
#相機旋轉角度 (for PICamera)
cameraRotate = 0
#拍攝的相片尺寸 (for PICamera)
photoSize = (1280, 720)
#一次要連拍幾張
numPics = 3
#間隔幾毫秒
picDelay = 0.1


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
    if(cameraType==0):
        from libraryCH.device.camera import PICamera
        camera = PICamera()
        camera.CameraConfig(rotation=180)  #相機旋轉角度
        camera.cameraResolution(resolution=(1280, 720))   #拍攝的相片尺寸

#從USB接收RFID 訊息
ser = serial.Serial('/dev/ttyACM1', 9600, timeout=1)

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

def displayUnknow(empNo, empName, uid):
    global lcd_LineNow

    st = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M')
    if(lcd_LineNow>0): lcd_nextLine()

    lcd.displayText("cfont1.ttf", fontSize=22, text=empNo, position=(lcd_Line2Pixel(lcd_LineNow), 240), fontColor=(253,244,6) )
    lcd.displayText("cfont1.ttf", fontSize=22, text=empName, position=(lcd_Line2Pixel(lcd_LineNow), 10) )

    lcd_nextLine()
    lcd.displayText("cfont1.ttf", fontSize=22, text=uid, position=(lcd_Line2Pixel(lcd_LineNow), 10) )

def speakWelcome(uid=""):
    dt = list(time.localtime())
    nowHour = dt[3]
    nowMinute = dt[4]

    mp3Number = str(random.randint(1, 3))

    if(nowHour<10 and nowHour>=5):
        if(uid=="200002"):
            logger.info("Speak welcome to Ku...")
            os.system('omxplayer --no-osd voice/a-ku.mp3')
        elif(uid=="200100"):
            os.system('omxplayer --no-osd voice/a-by.mp3')
        elif(uid=="200096"):
            os.system('omxplayer --no-osd voice/a-mi.mp3')
        else:
            os.system('omxplayer --no-osd voice/gowork' + mp3Number + '.mp3')

    if( (nowHour<22 and nowHour>=18) or (nowHour==17 and nowMinute>30 )):
        if(uid=="200002"):
            os.system('omxplayer --no-osd voice/b-ku.mp3')
        elif(uid=="200100"):
            os.system('omxplayer --no-osd voice/b-by.mp3')
        elif(uid=="200096"):
            os.system('omxplayer --no-osd voice/b-mi.mp3')
        else:
            os.system('omxplayer --no-osd voice/afterwork' + mp3Number + '.mp3')

def takePictures(saveFolder="others"):
    global picDelay, numPics, picturesPath, cameraType

    if(os.path.isdir(picturesPath+saveFolder)==False):
        os.makedirs(picturesPath+saveFolder)

    savePath = picturesPath + saveFolder + "/" + str(time.time())
    for i in range(0,numPics):
        if(cameraType==0 or cameraType==1):
            imagePath = savePath + "-" + str(i) + ".jpg"

            if(cameraType==0):
                camera.takePicture(imagePath)
            elif(cameraType==1):
                os.system('fswebcam -p YUYV -d /dev/video0 --no-banner -r 640x480 --rotate 90 ' + imagePath)

            logger.info("TakePicture " + str(i) + " to " + imagePath)
            time.sleep(picDelay)

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
mqttc.username_pw_set(MQTTuser, MQTTpwd)

#for tags read
lastTail = ""  #last TAG seen
lastTailTime = 0

#Problem or system hang
nodataProblem = 0  #目前是否發生無RFID data的問題

#-------------------------------------------------------------------------
#mqttc.connect(MQTTaddress, MQTTport, MQTTtimeout)
#mqttc.publish(ChannelPublish, '[{"Uid":"30-0-e2-0-81-81-81-6-2-55-13-50-8c-a9","EmpNo":"200002","EmpCName":"龔執豪","TagType":"E"}]')
#speakWelcome(uid="200002")
while True:

    try:
        lineRead = ser.readline()   # read a '\n' terminated line
    
    except Exception:
        logger.info("RFID serial port disconnected!")
        if(debugPrint==True): print("RFID serial port disconnected!")
        lineRead = ""
        pass
    #if(debugPrint==True): 
    #    print ("")
    #    print('Length: {}'.format(len(lineRead)))
    #    print(lineRead)
    #lineRead = lineRead.decode('ISO-8859-1')
    #if(debugPrint==True): print ( "converted to ISO-8859-1:" + lineRead)

    if(len(lineRead)>0):
        nodataProblem = 0

        lineRead = lineRead.decode('ISO-8859-1')
        if(debugPrint==True): print ( "converted to ISO-8859-1:" + lineRead)

        head = lineRead[:5].strip()
        tail = lineRead[5:].strip()
        if(debugPrint==True):
            print('lineRead[:5]={}  lineRead[5:]=={}'.format(head,tail))
            print('timer:{}   lastTag={}  nowTag={}'.format(time.time()-lastTailTime, lastTail, tail))

        if(head=="TAG:" and ((tail != lastTail) or (time.time()-lastTailTime>tagRepeatSeconds))):

            logger.info("Arduino: " + lineRead)
            try:
                webReply = urllib.request.urlopen(urlHeadString + tail).read()
                webReply = webReply.decode('utf-8').rstrip()
                #webReply = webReply.decode('ISO-8859-1').rstrip()
                logger.info('webReply: {}'.format(webReply))
                if(debugPrint==True):
                    print(urlHeadString + tail)
                    print("webReply:" + webReply)

            except Exception:
                print("Unexpected error:", sys.exc_info()[0])
                logger.info('Unexpected error:' + str(sys.exc_info()[0]))
                webReply = "[]"
                pass
           
            if(is_json(webReply)==True):
                jsonReply = json.loads(webReply)
                screenSaverNow = False

                if(len(jsonReply)>0):
                    #print ("JSON LEN:"+str(len(jsonReply)))
                    lastTail = tail
                    lastTailTime = time.time()

                    for i in range(0, len(jsonReply)):
                        logger.info('EmpNo:'+jsonReply[0]["EmpNo"]+'  EmpCName:'+jsonReply[i]["EmpCName"]+' Uid:'+jsonReply[i]["Uid"])

                        if ((jsonReply[i]["Uid"] not in lastUIDRead) or (time.time()-lastTimeRead>tagRepeatSeconds)):
                            if(debugPrint==True): print("Display on LCD screen.")
                            mqttc.connect(MQTTaddress, MQTTport, MQTTtimeout)
                            #mqttc.publish(ChannelPublish, jsonReply[0]["EmpNo"])
                            mqttc.publish(ChannelPublish, webReply)
                            logger.info('Display on screen and speak.')
                            displayUser(jsonReply[i]["EmpNo"], jsonReply[i]["EmpCName"], jsonReply[i]["Uid"])

                            if (jsonReply[i]["TagType"]=="E"):
                                speakWelcome(uid=str(jsonReply[i]["EmpNo"]))
                            elif (jsonReply[i]["TagType"]=="A"):
                                os.system('omxplayer --no-osd voice/warning1.mp3')

                            if(localCameraEnabled==True):
                                takePictures(str(jsonReply[0]["EmpNo"]))


                        logger.info('-------------------------------------------------')

                        if i==0: lastUIDRead=""
                        lastUIDRead += ","+jsonReply[i]["Uid"]
                        lastTimeRead = time.time()
                    

                else:
                    lengthTotal = len(lineRead)
               #     displayUnknow("未知TAG", lineRead[:int(lengthTotal/2)], lineRead[int(lengthTotal/2):])
                    logger.info('Unknow ID: ' + lineRead)
               #     lastUIDRead = lineRead
               #     lastTimeRead = time.time()

        if((time.time()-lastTimeRead)>screenSaverDelay and screenSaverNow==False):
            if(debugPrint==True): print("Display screen saveer.")
            logger.info("Display screen saveer.")
            lcd.displayImg("rfidbg.jpg")
            screenSaverNow = True

        if(debugPrint==True): print ("-------------------------------------------------------------------")

    else:
        if(nodataProblem==0):
            lcd.displayImg("rfidbg.jpg")
            screenSaverNow = True
            logger.info("Display screen saveer.")
            nodataProblem = 1

    try:
        ser.flushInput()

    except Exception:
        logger.info("RFID serial port disconnected!")
        if(debugPrint==True): print("RFID serial port disconnected!")
        lineRead = ""
        pass        

ser.close()
