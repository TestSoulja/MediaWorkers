import cv2
from colorama import Fore
import os

image_folder = r'D:\_Test\End\23'
video_name = 'video.avi'
counter = 0
files = os.listdir(image_folder)

images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
frame = cv2.imread(os.path.join(image_folder, images[0]))
height, width, layers = frame.shape

video = cv2.VideoWriter(video_name, 0, 25, (width,height))

for image in images:
    # video.write(cv2.imread(os.path.join(image_folder, image)))
    video.write(cv2.imread(os.path.join(image_folder, str(counter))+".png"))
    counter+=1
    print(Fore.YELLOW + f'\r[+] Сохраняю: {round(counter*100/len(files), 2)}/{100}', end='')

cv2.destroyAllWindows()
video.release()
