"""Загрузка видео: Rutube и YouTube."""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Sequence, Tuple

from .common import ensure_dir, info, require, warn

__all__ = ["DownloadReport", "download_rutube", "download_youtube"]


class DownloadReport(NamedTuple):
    downloaded: List[str]
    failed: List[Tuple[str, str]]


# ---------------------------------------------------------------------------
# Rutube
# ---------------------------------------------------------------------------


def download_rutube(
    urls: Sequence[str], output_dir="Downloads", quality: str = "best"
) -> DownloadReport:
    """Скачивает ролики Rutube в указанный каталог.

    :param quality: 'best' или разрешение, например '720'
    """
    Rutube = require("rutube").Rutube

    target = ensure_dir(output_dir)
    downloaded: List[str] = []
    failed: List[Tuple[str, str]] = []

    for index, url in enumerate(urls, start=1):
        info("[{}/{}] {}".format(index, len(urls), url))
        try:
            video = Rutube(url)
            if str(quality).lower() == "best":
                stream = video.get_best()
            else:
                by_resolution = getattr(video, "get_by_resolution", None)
                if by_resolution is None:
                    warn("Библиотека не умеет выбирать разрешение, беру лучшее")
                    stream = video.get_best()
                else:
                    stream = by_resolution(int(quality))
            stream.download(str(target))
            downloaded.append(url)
        except Exception as exc:  # сеть/парсинг/файловая система
            failed.append((url, str(exc)))
            warn("Ошибка: {}".format(exc))

    return DownloadReport(downloaded, failed)


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------


def _pick_stream(yt, quality: Optional[str]):
    """Выбирает progressive-поток нужного качества, иначе лучшее доступное."""
    progressive = yt.streams.filter(progressive=True, file_extension="mp4")
    if quality:
        exact = progressive.filter(res=quality).first()
        if exact is not None:
            return exact
        warn("Качество '{}' недоступно, беру максимальное".format(quality))
    candidates = list(progressive)
    if not candidates:
        candidates = list(yt.streams.filter(file_extension="mp4"))
    if not candidates:
        raise RuntimeError("Для видео нет доступных MP4-потоков")

    def height(stream) -> int:
        try:
            return int(str(stream.resolution).rstrip("p"))
        except (TypeError, ValueError):
            return 0

    return max(candidates, key=height)


def download_youtube(
    urls: Sequence[str], output_dir="Downloads", quality: Optional[str] = "360p"
) -> DownloadReport:
    """Скачивает видео YouTube через pytube."""
    YouTube = require("pytube").YouTube

    target = ensure_dir(output_dir)
    downloaded: List[str] = []
    failed: List[Tuple[str, str]] = []

    for index, url in enumerate(urls, start=1):
        info("[{}/{}] {}".format(index, len(urls), url))
        try:
            yt = YouTube(url)
            info("    {}".format(yt.title))
            stream = _pick_stream(yt, quality)
            info("    {} / {} fps".format(stream.resolution, getattr(stream, "fps", "?")))
            stream.download(output_path=str(target))
            downloaded.append(url)
        except Exception as exc:
            failed.append((url, str(exc)))
            warn("Ошибка: {}".format(exc))

    return DownloadReport(downloaded, failed)
