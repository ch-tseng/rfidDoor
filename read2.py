import serial

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

while True:
    rcv = ser.readline()
    cmd = rcv.decode('utf-8').rstrip()
