# MediaWorkers

Набор утилит для обработки изображений, видео и файлов: изменение размера,
рендер PDF, очистка дубликатов, склейка и сжатие видео, загрузка роликов.

Всё собрано в один пакет с общим CLI — вместо набора разрозненных скриптов
с жёстко прописанными путями.

## Установка

```bash
python -m pip install -r requirements.txt
```

Базово нужен только Python 3.7+. Зависимости подключаются лениво: например,
`count` и `dedupe` работают без Pillow, moviepy и OpenCV.

## Запуск

```bash
python main.py --help
python main.py <команда> --help
```

Или без `main.py`:

```bash
python -m mediaworkers --help
```

## Команды

### Изображения

```bash
# уменьшить все фото до 64x64 (результат рядом с исходниками)
python main.py resize ./photos -s 64x64

# в отдельный каталог, с сохранением пропорций
python main.py resize ./photos -o ./small -s 64x64 --keep-aspect

# PDF -> PNG (нужен poppler для pdf2image)
python main.py pdf2png ./doc.pdf -o ./pages --dpi 200
python main.py pdf2png ./docs --pages 1-3,5

# перенумеровать файлы: 4321.png, 4322.png, ...
python main.py rename ./Enter -o ./Exit --start 4321
```

### Файлы

```bash
# статистика по каталогу: количество, объём, расширения
python main.py count ./photos

# скопировать IMG_7598.jpg, IMG_7599.jpg ...
python main.py copy-names ./photo ./new 7598 7600 7613
python main.py copy-names ./photo ./new -f ids.txt --move

# удалить всё, где в имени есть "thumb"
python main.py delete-names ./voice_messages thumb --dry-run

# найти и удалить дубликаты по содержимому (сначала проверьте dry-run!)
python main.py dedupe ./photos --dry-run
python main.py dedupe ./photos
```

### Видео

```bash
# видео из последовательности кадров (естественная сортировка: 2 < 10)
python main.py photos-to-video ./frames -o video.mp4 --fps 25

# пережать в H.264/MP4 (по умолчанию в ./compressed)
python main.py compress ./videos --crf 28 --preset medium

# склеить ролики в один файл
python main.py merge ./Out -o ./Output/result.mp4
```

### Загрузка

```bash
python main.py dl-rutube -f links/rutube.txt -o Downloads
python main.py dl-rutube https://rutube.ru/video/... -q 720

python main.py dl-youtube -f links/youtube.txt -o Downloads -q 360p
```

## Тесты

```bash
python -m unittest discover -s tests -v
```

Тесты используют только стандартную библиотеку: проверяются сортировка,
разбор диапазонов, подсчёт, дубликаты, копирование и переименование.

## Структура

```
MediaWorkers/
├── main.py                 # точка входа
├── mediaworkers/
│   ├── cli.py              # разбор аргументов и команды
│   ├── common.py           # вывод, прогресс, поиск файлов, утилиты
│   ├── files.py            # подсчёт, копирование, дубликаты, переименование
│   ├── images.py           # ресайз, PDF -> PNG
│   ├── video.py            # кадры -> видео, сжатие, склейка
│   └── downloaders.py      # Rutube и YouTube
├── links/                  # списки ссылок
├── tests/                  # unittest-тесты
├── requirements.txt
└── README.md
```

## Что изменилось

| Было | Стало |
| --- | --- |
| `ChangePhotoSize.py` | `resize` |
| `PngToImage/main.py` | `pdf2png` |
| `RenameFile/RenamePhoto.py` | `rename` |
| `countFiles.py` | `count` |
| `CopyFilesOnNames.py` | `copy-names` |
| `DeleteOnName.py` | `delete-names` |
| `DeleteDuplicates.py` | `dedupe` |
| `VideoFromPhoto.py` | `photos-to-video` |
| `VideoCompression/main.py` | `compress` |
| `VideoUnion/main.py` | `merge` |
| `VideoDownloader/*.py` | `dl-rutube`, `dl-youtube` |

Главные улучшения:

- **Скорость.** Дубликаты ищутся по размеру и хешу (BLAKE2b), а не полным
  чтением каждого файла для каждого другого: было O(n²), стало ~O(n).
  Копирование по именам использует один проход по каталогу вместо вложенного
  перебора.
- **Безопасность.** Удаление и переименование поддерживают `--dry-run`,
  существующие файлы не перезаписываются без `--overwrite`, при
  переименовании в одном каталоге используется двухфазная замена.
- **Корректность.** Исправлен FPS при склейке (`fps=int(длительность)`),
  пропуск битых файлов вместо падения, естественная сортировка кадров,
  сохранение пропорций и EXIF-ориентации, корректный путь для PDF.
- **Гибкость.** Никаких прописанных путей — всё передаётся аргументами;
  параметры (размер, качество, CRF, FPS, шаблоны имён) настраиваются.
- **Чистота.** Общий код (прогресс, обход файлов) вынесен в `common.py`,
  тяжёлые зависимости импортируются только внутри нужных команд.
