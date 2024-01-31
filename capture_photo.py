from picamera2 import Picamera2, Preview
import time
import cv2

picam2 = Picamera2()

camera_config = picam2.create_still_configuration(main={"size": (640, 480)})
picam2.configure(camera_config)
picam2.start_preview(Preview.NULL)

picam2.start()
time.sleep(2)
picam2.capture_file("./imagenes/test01.jpg")

print("Foto tomada!")

img = cv2.imread('./imagenes/test01.jpg')
print(cv2.ROTATE_90_COUNTERCLOCKWISE)
img2 = cv2.rotate(img, cv2.ROTATE_180)
cv2.imwrite('./imagenes/test01_rot.jpg', img2)

print('Foto rotada!')
