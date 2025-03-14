from rutube import Rutube
import os

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')

links = ["https://rutube.ru/video/f9d5af87c94d112990dcf9137c72873d/",
         "https://rutube.ru/video/09218c1821cd41771750ebdde76dcbf6/",
         "https://rutube.ru/video/cef02bdcb723eb06ae759f3f7af7d7a9/",
         "https://rutube.ru/video/a2cf2517ffe99dd9be4837aaaac43699/",
         "https://rutube.ru/video/cb00d00340ddec3479cc767547ff89b4/",
         "https://rutube.ru/video/029c3cb92b19b5e9c86ccfb0de316dcc/",
         "https://rutube.ru/video/f4d124043f55fccbbcf30d958c0ccb62/",
         "https://rutube.ru/video/0d32dc8c9d6705b795cdf0b97a5c32d0/",
         "https://rutube.ru/video/b670c87292f965ce2a6ac59ae7b76066/",
         "https://rutube.ru/video/31713ff51680e5b7b2e536e520ce930e/"]

# Get a list of videos
# Each object is the same video but with different resolution
# print(rt.playlist)  # [Nature 4k (272x480), Nature 4k (408x720), Nature 4k (608x1080)]

# Get a list of available resolutions
# print(rt.available_resolutions)  # [480, 720, 1080]

for i in links:
    rt = Rutube(i)
    rt.get_best().download(c)