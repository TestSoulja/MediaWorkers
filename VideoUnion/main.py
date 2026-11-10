import os.path
from pathlib import Path
import time

from colorama import Fore
from moviepy.editor import VideoFileClip, concatenate_videoclips


# Получаем абсолютный путь к скрипту и родительскую директорию
s = Path(__file__).resolve()
c = str(s.parent)


directory = r'D:\_Test\Out'


def merge_video_clip(path_directory: str, res_name: str):
    """Объединяет все видеофайлы из указанной директории в один MP4 файл."""

    # Нормализуем путь (добавляем слэш в конце, если нужно)
    path_directory = Path(path_directory).as_posix()
    if not path_directory.endswith('/'):
        path_directory += '/'

    print(Fore.CYAN + f'[+] Сканирование директории: {path_directory}')

    # Получаем список всех файлов (не папок)
    files_in_dir = [f for f in os.listdir(path_directory) if os.path.isfile(os.path.join(path_directory, f))]

    if not files_in_dir:
        print(Fore.YELLOW + '[-] Директория пуста или содержит только 1 файл')
        return

    clip_to_merge = []

    # Проходим по файлам с нумерацией
    for idx, clip in enumerate(files_in_dir, 1):
        clip_path = os.path.join(path_directory, clip)

        print(Fore.GREEN + f'    [{idx}/{len(files_in_dir)}] {clip}')

        try:
            v = VideoFileClip(clip_path, preserve_names=True)
            clip_to_merge.append(v)
        except Exception as e:
            print(Fore.RED + f'        [!] Ошибка с файлом "{clip}": {e}')

    if len(clip_to_merge) == 0:
        print(Fore.YELLOW + '[-] Ничего не было добавлено в список клипов')
        return
    
    print(Fore.YELLOW + f'\n[+] Найдено файлов для объединения: {len(clip_to_merge)}')

    # Считаем общую длительность
    total_duration = sum(c.duration for c in clip_to_merge)
    duration_str = time.strftime("%H:%M:%S", time.gmtime(total_duration))

    print(Fore.YELLOW + f'[+] Длительность объединяемого видео: {duration_str}\n')

    # Объединяем все клипы
    merge_final = concatenate_videoclips(clip_to_merge)

    print('[+] Начинаю объединение файлов...')

    # Создаём директорию вывода, если нужно
    output_dir = Path(c + '/Output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Имя итогового файла
    output_filename = f'{res_name}.mp4'
    output_path = output_dir / output_filename

    # Пишем итоговый файл с настройками производительности
    merge_final.write_videofile(
        str(output_path),
        fps=int(total_duration) if total_duration > 30 else 25,  # FPS на основе длительности
        remove_temp=True  # Удаляет временные файлы после завершения
    )

    print(Fore.GREEN + '\n[+] Объединение файлов завершено!')
    print(Fore.GREEN + f'[+] Видео сохранено в: "{output_path}"')


# Запускаем функцию с текущей директорией и именем "29"
merge_video_clip(directory, '29')