import os.path
import time
from numpy import arange
import json

from colorama import Fore
from colorama import init
from moviepy.editor import *

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')


directory = r'D:\_Test\Out'


def merge_video_clip(path_directory, res_name):
    if os.path.exists(path_directory):
        print(Fore.CYAN + '[+] Сканирование директории')
        clip_in_dir = os.listdir(path_directory)
        clip_to_merge = []
        for clip in clip_in_dir:
            # VideoFileClip(os.path.join(path_directory, clip))
            clip_to_merge.append(VideoFileClip(os.path.join(path_directory, clip)))


        print(Fore.YELLOW + f'[+] Найдено фалов: {len(clip_to_merge)}')
        merge_final = concatenate_videoclips(clip_to_merge)
        print(Fore.YELLOW + f'[+] Длительность объединяемого видео: '
              f'{time.strftime("%H:%M:%S", time.gmtime(merge_final.duration))}\n[+] Начинаю объединение файлов...\n')
        merge_final.write_videofile(c+"Output\\"+ f'{res_name}.mp4')
        print(Fore.GREEN + '\n[+] Объединение файлов завершено')
        print(Fore.GREEN + f'[+] Видео сохранено в папку: "{c +"Output/"+ f"{res_name}.mp4"}"')
        return
    else:
        print(Fore.RED + '[-] Указанного пути не существует')
        return
    
merge_video_clip(directory, "6")