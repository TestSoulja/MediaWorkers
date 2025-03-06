from rutube import Rutube
import os

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')

links = ["https://rutube.ru/video/e3a32b3f95f31697ef6886cbaf593a6f/",
         "https://rutube.ru/video/b54105442173ccf5f5f309e175e43c49/",
         "https://rutube.ru/video/9da22dac41bca1b3b342acbc2094d977/",
         "https://rutube.ru/video/67d14a48d82b7254630141bc23a808f7/",
         "https://rutube.ru/video/434c29e794da0426b285995501fec61f/",
         "https://rutube.ru/video/03064a86780ab58c0ef466fd9f287a51/",
         "https://rutube.ru/video/930eee0a808ec62ebb357580e5e7817f/",
         "https://rutube.ru/video/0dfacac9c6f024ef6c50b61bb0f4daf9/"]

# Get a list of videos
# Each object is the same video but with different resolution
# print(rt.playlist)  # [Nature 4k (272x480), Nature 4k (408x720), Nature 4k (608x1080)]

# Get a list of available resolutions
# print(rt.available_resolutions)  # [480, 720, 1080]

for i in links:
    rt = Rutube(i)
    rt.get_best().download(c)
