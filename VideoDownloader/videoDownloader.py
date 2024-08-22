from pytubefix import YouTube
from pytubefix.cli import on_progress
import os

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')

c = "C:/Users/TeSoul/YandexDisk/Youtube"

url = "https://www.youtube.com/watch?v=IzFy83zbN3o"
# url = "https://youtu.be/2NmMyz9V0s4?si=uMO91Z6jNNSurfuJ"
 
yt = YouTube(url, on_progress_callback = on_progress)
print(yt.title)
 
ys = yt.streams.get_highest_resolution()
ys.download(c)

print("OK")
