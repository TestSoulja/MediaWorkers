from rutube import Rutube
import os

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')

links = ["https://rutube.ru/video/7b3186887d88c16861103823c8543902/",
         "https://rutube.ru/video/f88dba2792fd9b1b82a18f3a482047b0/",
         "https://rutube.ru/video/e0516392a941b80e611166a567ea81c5/",
         "https://rutube.ru/video/0e7034b133383e43382968b601732066/",
         "https://rutube.ru/video/be72437b519cfeeb11fb38f4b6a6c20a/",
         "https://rutube.ru/video/52086e09004fbd59e0ca995dac9eeca5/",
         "https://rutube.ru/video/8d563c4e76a2f7df34e3974110afc0ff/",
         "https://rutube.ru/video/73ffb5afb3ee62820828477182797e62/",
         "https://rutube.ru/video/a923a394cf054a7435fed3f82fb1776e/",
         "https://rutube.ru/video/b4b72c4b01c132017db8d82bf3e8f5dd/"]

# Get a list of videos
# Each object is the same video but with different resolution
# print(rt.playlist)  # [Nature 4k (272x480), Nature 4k (408x720), Nature 4k (608x1080)]

# Get a list of available resolutions
# print(rt.available_resolutions)  # [480, 720, 1080]

for i in links:
    rt = Rutube(i)
    rt.get_best().download(c+"exit")