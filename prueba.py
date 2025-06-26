import serial
import time

try:
    ser = serial.Serial('COM7', 9600, timeout=1)
    print("Puerto abierto correctamente.")
    time.sleep(2)
    ser.close()
    print("Puerto cerrado.")
except Exception as e:
    print("Error conectando al puerto serial:", e)
