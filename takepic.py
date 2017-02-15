#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time, os
import paho.mqtt.client as mqtt
from libraryCH.device.camera import PICamera

camera = PICamera()
camera.CameraConfig(rotation=180)  #相機旋轉角度
camera.cameraResolution(resolution=(1280, 720))   #拍攝的相片尺寸

#MQTT
ChannelPublish = "Door-camera"
MQTTuser = "chtseng"
MQTTpwd = "chtseng"
MQTTaddress = "akai-chen-pc3.sunplusit.com.tw"
MQTTport = 1883
MQTTtimeout = 60


def on_connect(mosq, obj, rc):
    mqttc.subscribe("Door-camera", 0)
    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    global message
    #print(msg.topic + "/ " + str(msg.qos) + "/ " + str(msg.payload))
    print ("Received: " + str(msg.payload))
    if(os.path.isdir("/var/www/html/rfidface/"+str(msg.payload))==False):
        os.makedirs("/var/www/html/rfidface/"+str(msg.payload))

    print ("Take picture!!")
    camera.takePicture("/var/www/html/rfidface/"+str(msg.payload)+"/"+str(time.time())+".jpg")

def on_publish(mosq, obj, mid):
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
mqttc.connect(MQTTaddress, MQTTport, MQTTtimeout)

#mqttc = mqtt.Client()
#mqttc.on_message = on_message
#mqttc.on_connect = on_connect
#mqttc.on_publish = on_publish
#mqttc.on_subscribe = on_subscribe
#user = "chtseng"
#password = "chtseng"
#mqttc.username_pw_set(user, password)
#mqttc.connect("akai-chen-pc3.sunplusit.com.tw", 1883,60)


# Continue the network loop
mqttc.loop_forever()
