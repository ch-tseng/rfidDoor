import serial
ser = serial.Serial('/dev/ttyS0', 9600)
while True :
    try:
        state=serial.readline()
        print(state)
    except:
        pass
