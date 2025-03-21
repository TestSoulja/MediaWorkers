from rutube import Rutube
import os

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')

links = [""]

# Get a list of videos
# Each object is the same video but with different resolution
# print(rt.playlist)  # [Nature 4k (272x480), Nature 4k (408x720), Nature 4k (608x1080)]

# Get a list of available resolutions
# print(rt.available_resolutions)  # [480, 720, 1080]

for i in links:
    rt = Rutube(i)
    rt.get_best().download(c)