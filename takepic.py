#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time, os
import logging
import paho.mqtt.client as mqtt
from libraryCH.device.camera import PICamera

#MQTT設定---------------------------------------
ChannelPublish = "Door-camera"
MQTTuser = "chtseng"
MQTTpwd = "chtseng"
MQTTaddress = "akai-chen-pc3.sunplusit.com.tw"
MQTTport = 1883
MQTTtimeout = 60

#拍照設定--------------------------------------
#儲放相片的主目錄
picturesPath = "/var/www/html/rfidface/"
#相機旋轉角度
cameraRotate = 180
#拍攝的相片尺寸
photoSize = (1280, 720)
#一次要連拍幾張
numPics = 10
#間隔幾毫秒
picDelay = 0.5 

#---------------------------------------------------------
#You don't have to modify the code below------------------
#---------------------------------------------------------
camera = PICamera()
camera.CameraConfig(rotation=cameraRotate)  
camera.cameraResolution(resolution=photoSize)

#logging記錄
logger = logging.getLogger('msg')
hdlr = logging.FileHandler('/home/pi/RFIDcamera/msg.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)


def takePictures(saveFolder="others"):
    global picDelay, numPics, picturesPath

    if(os.path.isdir(picturesPath+saveFolder)==False):
        os.makedirs(picturesPath+saveFolder)

    savePath = picturesPath + saveFolder + "/" + str(time.time())
    for i in range(0,numPics):
        camera.takePicture(savePath + "-" + str(i) + ".jpg")
        logger.info("TakePicture " + str(i) + " to " + savePath + "-" + str(i) + ".jpg")
        time.sleep(picDelay)

def on_connect(mosq, obj, rc):
    mqttc.subscribe("Door-camera", 0)
    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    global message
    #print(msg.topic + "/ " + str(msg.qos) + "/ " + str(msg.payload))
    msgReceived = str(msg.payload.decode("utf-8"))
    print ("Received: " + msgReceived)
    logger.info("MQTT received: " + msgReceived)
    takePictures(msgReceived)

def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))
    logger.info("MQTT subscribed: " + str(mid) + " " + str(granted_qos))

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
mqttc.connect(MQTTaddress, MQTTport, MQTTtimeout)

# Continue the network loop
mqttc.loop_forever()
