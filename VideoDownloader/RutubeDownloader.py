from rutube import Rutube
import os

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')

links = ["https://rutube.ru/video/f93b891f523fb3fa3429c8e7dd37578c/?playlist=525381",
         "https://rutube.ru/video/6fcbe836d7b255d122a97daeb5ad219d/?playlist=525381",
         "https://rutube.ru/video/ae79c4cb9432cb4e4a59f69801c59fe7/?playlist=525381",
         "https://rutube.ru/video/893ccbce38e557288c190b78fe2dc9cf/?playlist=525381",
         "https://rutube.ru/video/421ce09dc28d36b2b2d04d4d899c4d15/?playlist=525381",
         "https://rutube.ru/video/44dc343561bac543c22ed0fa86d0af6c/?playlist=525381",
         "https://rutube.ru/video/8dbef0758cbd9df033aaced57e9a12a8/?playlist=525381",
         "https://rutube.ru/video/1ea38dd435f8bef78896dc5128e8b6c6/?playlist=525381",
         "https://rutube.ru/video/e96633e4ad3ffbca95c858771b894648/?playlist=525381",
         "https://rutube.ru/video/b358ac3e14941fde49035df99ca21aa8/?playlist=525381",
         "https://rutube.ru/video/a62b3d97280de3f2825a4101f7e8aee5/?playlist=525381",
         "https://rutube.ru/video/e4edaee1c8f2cce2edec6451da17c5c2/?playlist=525381"]

# Get a list of videos
# Each object is the same video but with different resolution
# print(rt.playlist)  # [Nature 4k (272x480), Nature 4k (408x720), Nature 4k (608x1080)]

# Get a list of available resolutions
# print(rt.available_resolutions)  # [480, 720, 1080]

for i in links:
    rt = Rutube(i)
    rt.get_best().download(c)