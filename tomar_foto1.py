# Tomar una foto
from picamera2 import Picamera2

picam = Picamera2()

picam.start_and_capture_file("foto2.jpg")

print("Foto tomada!")

