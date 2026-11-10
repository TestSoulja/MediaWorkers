"""Командная строка MediaWorkers.

Пример:
    python main.py resize ./photos -o ./out -s 64x64
    python main.py dedupe ./photos --dry-run
    python main.py merge ./clips -o merged.mp4
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Callable, List, Optional, Sequence

from . import __version__
from .common import (
    IMAGE_SUFFIXES,
    error,
    format_duration,
    human_size,
    info,
    parse_name_list,
    read_list_file,
    success,
    warn,
)
from .downloaders import download_rutube, download_youtube
from .files import (
    copy_by_names,
    count_files,
    delete_by_name,
    delete_duplicates,
    rename_files,
)
from .images import pdf_to_png, resize_images
from .video import compress_videos, merge_videos, photos_to_video

__all__ = ["build_parser", "main"]

_SIZE_RE = re.compile(r"^\s*(\d+)\s*[xх*\u00d7]\s*(\d+)\s*$", re.IGNORECASE)


def _size(value: str):
    match = _SIZE_RE.match(value)
    if not match:
        raise argparse.ArgumentTypeError("Ожидается формат ШИРИНАxВЫСОТА, например 64x64")
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Размер должен быть положительным")
    return width, height


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Ожидается целое число")
    if number <= 0:
        raise argparse.ArgumentTypeError("Значение должно быть больше нуля")
    return number


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Ожидается целое число")
    if number < 0:
        raise argparse.ArgumentTypeError("Значение не может быть отрицательным")
    return number


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Ожидается число")
    if number <= 0:
        raise argparse.ArgumentTypeError("Значение должно быть больше нуля")
    return number


def _add_progress_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="не показывать прогресс"
    )


def _add_dry_run_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="только показать, что будет сделано, без изменений на диске",
    )


# ---------------------------------------------------------------------------
# Обработчики команд
# ---------------------------------------------------------------------------


def _cmd_resize(args: argparse.Namespace) -> int:
    report = resize_images(
        args.source,
        args.output,
        size=args.size,
        keep_aspect=args.keep_aspect,
        quality=args.quality,
        recursive=args.recursive,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        show_progress=not args.quiet,
    )
    if args.dry_run:
        info("Будет обработано файлов: {}".format(len(report.resized)))
    else:
        success(
            "Готово: изменено {}, пропущено {}".format(
                len(report.resized), len(report.skipped)
            )
        )

    for path, message in report.errors:
        error("{}: {}".format(path, message))
    return 1 if report.errors else 0


def _cmd_pdf2png(args: argparse.Namespace) -> int:
    report = pdf_to_png(args.source, args.output, pages=args.pages, dpi=args.dpi)
    success("Создано страниц: {}".format(len(report.created)))
    for path, message in report.errors:
        error("{}: {}".format(path, message))
    return 1 if report.errors else 0


def _cmd_rename(args: argparse.Namespace) -> int:
    suffixes = {
        ext.lower() if ext.startswith(".") else "." + ext.lower() for ext in args.ext
    }
    report = rename_files(
        args.source,
        args.output,
        start=args.start,
        pattern=args.pattern,
        suffixes=suffixes,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        info("Будет переименовано: {}".format(len(report.renamed)))
    else:
        success(
            "Переименовано: {}, пропущено: {}".format(
                len(report.renamed), len(report.skipped)
            )
        )
    for path, message in report.errors:
        error("{}: {}".format(path, message))
    return 1 if report.errors else 0


def _cmd_count(args: argparse.Namespace) -> int:
    result = count_files(args.directory, recursive=not args.no_recursive)
    info("Файлов: {}".format(result.files))
    info("Объём:  {}".format(human_size(result.total_size)))
    info("Время:  {:.2f} с".format(result.elapsed))

    if args.top and result.by_extension:
        info("\nРасширения:")
        ranked = sorted(
            result.by_extension.items(), key=lambda item: item[1][0], reverse=True
        )
        width = max(len(ext) for ext, _ in ranked[: args.top])
        for ext, (count, size) in ranked[: args.top]:
            info("  {:<{w}}  {:>8}  {:>10}".format(ext, count, human_size(size), w=width))
    return 0


def _cmd_copy(args: argparse.Namespace) -> int:
    names = parse_name_list(args.ids)
    if args.ids_file:
        names.extend(parse_name_list(read_list_file(args.ids_file)))
    names = parse_name_list(names)
    if not names:
        error("Не заданы имена/id (укажите позиционно или через --ids-file)")
        return 2

    report = copy_by_names(
        args.source,
        args.destination,
        names,
        pattern=args.pattern,
        move=args.move,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    action = "перемещено" if args.move else "скопировано"
    if args.dry_run:
        info("Будет {}: {}".format(action, len(report.copied)))
    else:
        success("Итого {}: {}".format(action, len(report.copied)))
    if report.skipped:
        warn("Пропущено (уже существует): {}".format(len(report.skipped)))
    if report.missing:
        warn(
            "Не найдено: {} ({})".format(
                len(report.missing), ", ".join(report.missing[:10])
            )
        )

    for name, message in report.errors:
        error("{}: {}".format(name, message))
    return 1 if report.errors else 0


def _cmd_delete_names(args: argparse.Namespace) -> int:
    report = delete_by_name(
        args.directory,
        args.substring,
        recursive=args.recursive,
        ignore_case=not args.case_sensitive,
        dry_run=args.dry_run,
    )
    prefix = "Будет удалено" if args.dry_run else "Удалено"
    info("{}: {} ({})".format(prefix, len(report.removed), human_size(report.freed)))
    for path, message in report.errors:
        error("{}: {}".format(path, message))
    return 1 if report.errors else 0


def _cmd_dedupe(args: argparse.Namespace) -> int:
    report = delete_duplicates(
        args.directory,
        recursive=args.recursive,
        dry_run=args.dry_run,
        min_size=args.min_size,
        show_progress=not args.quiet,
    )
    prefix = "Будет удалено" if args.dry_run else "Удалено"
    success(
        "Групп дубликатов: {}, {} файлов: {} ({})".format(
            report.groups, prefix.lower(), len(report.removed), human_size(report.freed)
        )
    )
    for path, message in report.errors:
        error("{}: {}".format(path, message))
    return 1 if report.errors else 0


def _cmd_photos_to_video(args: argparse.Namespace) -> int:
    report = photos_to_video(
        args.folder, args.output, fps=args.fps, show_progress=not args.quiet
    )
    if report.output is None:
        warn("Видео не создано")
        return 1
    success(
        "Видео: {} ({} кадров, {:.1f} FPS)".format(
            report.output, report.frames, args.fps
        )
    )
    if report.skipped:
        warn("Пропущено кадров: {}".format(len(report.skipped)))
    return 0


def _cmd_compress(args: argparse.Namespace) -> int:
    report = compress_videos(
        args.source,
        args.output,
        crf=args.crf,
        preset=args.preset,
        audio_bitrate=args.audio_bitrate,
        recursive=not args.no_recursive,
        overwrite=args.overwrite,
        show_progress=not args.quiet,
    )
    success("Сжато: {}, пропущено: {}".format(len(report.compressed), len(report.skipped)))
    for path, message in report.errors:
        error("{}: {}".format(path, message))
    return 1 if report.errors else 0


def _cmd_merge(args: argparse.Namespace) -> int:
    report = merge_videos(
        args.source,
        args.output,
        fps=args.fps,
        recursive=args.recursive,
        show_progress=not args.quiet,
    )
    if report.output is None:
        warn("Видео не создано")
        return 1
    success(
        "Готово: {} ({} клипов, {})".format(
            report.output, report.clips, format_duration(report.duration)
        )
    )
    if report.skipped:
        warn("Пропущено клипов: {}".format(len(report.skipped)))
    return 0


def _collect_urls(values: Sequence[str], links_file: Optional[str]) -> List[str]:
    urls = [value.strip() for value in values if value.strip()]
    if links_file:
        urls.extend(read_list_file(links_file))
    return urls


def _cmd_dl_rutube(args: argparse.Namespace) -> int:
    urls = _collect_urls(args.urls, args.links_file)
    if not urls:
        error("Не заданы ссылки (позиционно или через --links-file)")
        return 2
    report = download_rutube(urls, args.output, quality=args.quality)
    success("Скачано: {} из {}".format(len(report.downloaded), len(urls)))
    for url, message in report.failed:
        error("{}: {}".format(url, message))
    return 1 if report.failed else 0


def _cmd_dl_youtube(args: argparse.Namespace) -> int:
    urls = _collect_urls(args.urls, args.links_file)
    if not urls:
        error("Не заданы ссылки (позиционно или через --links-file)")
        return 2
    report = download_youtube(urls, args.output, quality=args.quality)
    success("Скачано: {} из {}".format(len(report.downloaded), len(urls)))
    for url, message in report.failed:
        error("{}: {}".format(url, message))
    return 1 if report.failed else 0


# ---------------------------------------------------------------------------
# Парсер
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mediaworkers",
        description="Утилиты для обработки изображений, видео и файлов.",
        usage="%(prog)s <команда> [параметры]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = parser.add_subparsers(dest="command", required=True, metavar="<команда>")

    # -- изображения --------------------------------------------------------
    p = sub.add_parser(
        "resize",
        help="изменить размер изображений",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("source", help="каталог с изображениями")
    p.add_argument("-o", "--output", help="каталог результата (по умолчанию — исходный)")
    p.add_argument("-s", "--size", type=_size, default=(64, 64), metavar="WxH")
    p.add_argument("--keep-aspect", action="store_true", help="сохранять пропорции")
    p.add_argument("--quality", type=_non_negative_int, default=95, help="качество JPEG/WebP")
    p.add_argument("-r", "--recursive", action="store_true", help="обойти вложенные каталоги")
    p.add_argument("--overwrite", action="store_true", help="перезаписывать существующие файлы")
    _add_dry_run_arg(p)
    _add_progress_arg(p)
    p.set_defaults(handler=_cmd_resize)

    p = sub.add_parser(
        "pdf2png",
        help="отрендерить PDF в PNG",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("source", help="PDF-файл или каталог с PDF")
    p.add_argument("-o", "--output", help="каталог результата")
    p.add_argument("--pages", default="ALL", help="страницы: ALL или 1-3,5")
    p.add_argument("--dpi", type=_positive_int, default=200)
    p.set_defaults(handler=_cmd_pdf2png)

    p = sub.add_parser(
        "rename",
        help="перенумеровать файлы по шаблону",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("source", help="каталог с файлами")
    p.add_argument("-o", "--output", help="каталог результата (по умолчанию — исходный)")
    p.add_argument("--start", type=_non_negative_int, default=1, help="первый номер")
    p.add_argument(
        "-p",
        "--pattern",
        default="{n}{ext}",
        help="шаблон имени; поля: {n}, {name}, {ext}",
    )
    p.add_argument(
        "--ext",
        nargs="+",
        default=sorted(IMAGE_SUFFIXES),
        metavar="EXT",
        help="какие расширения обрабатывать",
    )
    p.add_argument("--overwrite", action="store_true", help="перезаписывать существующие файлы")
    _add_dry_run_arg(p)
    p.set_defaults(handler=_cmd_rename)

    # -- файлы --------------------------------------------------------------
    p = sub.add_parser(
        "count",
        help="посчитать файлы и их объём",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("directory")
    p.add_argument("--no-recursive", action="store_true", help="не обходить вложенные каталоги")
    p.add_argument(
        "--top",
        type=_non_negative_int,
        default=10,
        help="сколько расширений показать (0 — скрыть)",
    )

    p.set_defaults(handler=_cmd_count)

    p = sub.add_parser(
        "copy-names",
        help="скопировать/переместить файлы по id или именам",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("source", help="каталог-источник")
    p.add_argument("destination", help="каталог-приёмник")
    p.add_argument(
        "ids",
        nargs="*",
        help="id/имена; поддерживаются диапазоны 100-105 и список 1,2,3",
    )

    p.add_argument("-f", "--ids-file", help="файл со списком id (по одному в строке)")
    p.add_argument("-p", "--pattern", default="IMG_{id}.jpg", help="шаблон имени, поле {id}")
    p.add_argument("--move", action="store_true", help="перемещать вместо копирования")
    p.add_argument("--overwrite", action="store_true", help="перезаписывать существующие файлы")
    _add_dry_run_arg(p)
    p.set_defaults(handler=_cmd_copy)

    p = sub.add_parser(
        "delete-names",
        help="удалить файлы, в имени которых есть подстрока",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("directory")
    p.add_argument("substring", help="подстрока для поиска в имени файла")
    p.add_argument("-r", "--recursive", action="store_true", help="обойти вложенные каталоги")
    p.add_argument("--case-sensitive", action="store_true", help="учитывать регистр")
    _add_dry_run_arg(p)
    p.set_defaults(handler=_cmd_delete_names)

    p = sub.add_parser(
        "dedupe",
        help="удалить файлы-дубликаты (по содержимому)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("directory")
    p.add_argument("-r", "--recursive", action="store_true", help="обойти вложенные каталоги")
    p.add_argument("--min-size", type=_non_negative_int, default=0, help="минимальный размер, байт")
    _add_dry_run_arg(p)
    _add_progress_arg(p)
    p.set_defaults(handler=_cmd_dedupe)

    # -- видео --------------------------------------------------------------
    p = sub.add_parser(
        "photos-to-video",
        help="собрать видео из изображений",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("folder", help="каталог с кадрами")
    p.add_argument("-o", "--output", help="выходной файл")
    p.add_argument("--fps", type=_positive_float, default=25.0)
    _add_progress_arg(p)
    p.set_defaults(handler=_cmd_photos_to_video)

    p = sub.add_parser(
        "compress",
        help="пережать видео в MP4 (H.264)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("source", help="файл или каталог с видео")
    p.add_argument("-o", "--output", help="каталог или файл результата")
    p.add_argument("--crf", type=_non_negative_int, default=28, help="качество: меньше — лучше")
    p.add_argument("--preset", default="medium", help="пресет x264: ultrafast..veryslow")
    p.add_argument("--audio-bitrate", default="128k")
    p.add_argument("--no-recursive", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="пережимать даже готовые файлы")
    _add_progress_arg(p)
    p.set_defaults(handler=_cmd_compress)

    p = sub.add_parser(
        "merge",
        help="склеить видео в один файл",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("source", help="каталог с видео")
    p.add_argument("-o", "--output", help="выходной файл")
    p.add_argument("--fps", type=_positive_float, help="итоговый FPS (по умолчанию — из клипов)")
    p.add_argument("-r", "--recursive", action="store_true", help="обойти вложенные каталоги")
    _add_progress_arg(p)
    p.set_defaults(handler=_cmd_merge)

    # -- загрузка -----------------------------------------------------------
    p = sub.add_parser(
        "dl-rutube",
        help="скачать видео с Rutube",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("urls", nargs="*", help="ссылки на видео")
    p.add_argument("-f", "--links-file", help="файл со ссылками")
    p.add_argument("-o", "--output", default="Downloads", help="каталог загрузки")
    p.add_argument("-q", "--quality", default="best", help="best или разрешение, например 720")
    p.set_defaults(handler=_cmd_dl_rutube)

    p = sub.add_parser(
        "dl-youtube",
        help="скачать видео с YouTube",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("urls", nargs="*", help="ссылки на видео")
    p.add_argument("-f", "--links-file", help="файл со ссылками")
    p.add_argument("-o", "--output", default="Downloads", help="каталог загрузки")
    p.add_argument("-q", "--quality", default="360p", help="например 360p, 720p")
    p.set_defaults(handler=_cmd_dl_youtube)

    return parser


def _configure_stdio() -> None:
    """UTF-8 для перенаправленного вывода: логи и пайпы не ломают кириллицу."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            if not getattr(stream, "isatty", lambda: False)():
                reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except KeyboardInterrupt:
        error("\nПрервано пользователем")
        return 130
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError, ImportError) as exc:
        error(str(exc))
        return 1
    except OSError as exc:
        error("Ошибка файловой системы: {}".format(exc))
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
