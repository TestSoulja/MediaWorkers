"""Видео: сборка из кадров, сжатие и склейка."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence, Tuple, Union

from .common import (
    VIDEO_SUFFIXES,
    Progress,
    format_duration,
    info,
    is_under,
    iter_files,
    natural_key,
    require,
    warn,
)

__all__ = [
    "CompressReport",
    "MergeReport",
    "PhotoVideoReport",
    "compress_videos",
    "merge_videos",
    "photos_to_video",
]


class PhotoVideoReport(NamedTuple):
    output: Optional[Path]
    frames: int
    skipped: List[Path]


class CompressReport(NamedTuple):
    compressed: List[Path]
    skipped: List[Path]
    errors: List[Tuple[Path, str]]


class MergeReport(NamedTuple):
    output: Optional[Path]
    clips: int
    duration: float
    skipped: List[Path]


# ---------------------------------------------------------------------------
# Кадры -> видео
# ---------------------------------------------------------------------------


def _video_writer(cv2, output: Path, fps: float, size: Tuple[int, int]):
    """Подбирает кодек по расширению и создаёт VideoWriter."""
    fourcc_name = "mp4v" if output.suffix.lower() in (".mp4", ".m4v", ".mov") else "MJPG"
    fourcc = cv2.VideoWriter_fourcc(*fourcc_name)
    return cv2.VideoWriter(str(output), fourcc, float(fps), size)


def photos_to_video(
    folder,
    output=None,
    fps: float = 25.0,
    show_progress: bool = True,
) -> PhotoVideoReport:
    """Собирает видео из изображений каталога в естественном порядке."""
    cv2 = require("cv2", "opencv-python")

    source = Path(folder)
    files = iter_files(source, suffixes={".png", ".jpg", ".jpeg", ".bmp", ".webp"})
    if not files:
        raise FileNotFoundError("В '{}' нет изображений".format(source))
    if fps <= 0:
        raise ValueError("FPS должен быть больше нуля")

    first = cv2.imread(str(files[0]))
    if first is None:
        raise RuntimeError("Не удалось прочитать первое изображение: {}".format(files[0]))
    height, width = first.shape[:2]

    target = Path(output) if output else source / "video.mp4"
    if not target.suffix:
        target = target.with_suffix(".mp4")
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)

    writer = _video_writer(cv2, target, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(
            "Не удалось открыть VideoWriter для '{}'. Проверьте кодек/расширение.".format(
                target
            )
        )

    skipped: List[Path] = []
    written = 0
    progress = Progress(len(files), "Кадры", enabled=show_progress)
    try:
        for path in files:
            frame = cv2.imread(str(path))
            if frame is None:
                skipped.append(path)
                warn("Кадр не прочитан: {}".format(path.name))
                progress.update()
                continue
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            writer.write(frame)
            written += 1
            progress.update(note=path.name)
    finally:
        writer.release()
        progress.close()

    return PhotoVideoReport(target, written, skipped)


# ---------------------------------------------------------------------------
# Сжатие
# ---------------------------------------------------------------------------


def _video_clip_class():
    """VideoFileClip из moviepy 1.x или 2.x."""
    try:
        from moviepy.editor import VideoFileClip  # moviepy < 2
    except ImportError:
        from moviepy import VideoFileClip  # moviepy >= 2
    return VideoFileClip


def _resolve_video_files(source: Path, recursive: bool) -> List[Path]:
    if source.is_file():
        return [source] if source.suffix.lower() in VIDEO_SUFFIXES else []
    return iter_files(source, recursive=recursive, suffixes=VIDEO_SUFFIXES)


def compress_videos(
    source,
    destination=None,
    crf: int = 28,
    preset: str = "medium",
    audio_bitrate: str = "128k",
    recursive: bool = True,
    overwrite: bool = False,
    show_progress: bool = True,
) -> CompressReport:
    """Пережимает видео в MP4 (H.264/AAC), пропуская готовые файлы."""
    VideoFileClip = _video_clip_class()

    src = Path(source)
    if not src.exists():
        raise FileNotFoundError("Путь не найден: {}".format(src))

    files = _resolve_video_files(src, recursive)

    if destination is not None:
        dst = Path(destination)
        # Путь без расширения считаем каталогом; с расширением — файлом (для одного источника).
        single_target = dst.suffix.lower() in VIDEO_SUFFIXES
        suffix = ""
        if single_target and len(files) > 1:
            raise ValueError(
                "Нельзя указать один выходной файл для {} исходников".format(len(files))
            )
        if not single_target:
            dst.mkdir(parents=True, exist_ok=True)
    elif src.is_file():
        # Не перезаписываем исходник: результат получает суффикс.
        dst = src.parent
        single_target = False
        suffix = "_compressed"
    else:
        dst = src / "compressed"
        dst.mkdir(parents=True, exist_ok=True)
        single_target = False
        suffix = ""

    if not single_target:
        # Не пережимаем собственный вывод при повторном запуске.
        files = [path for path in files if not is_under(path, dst)]
    if not files:
        warn("Видеофайлы не найдены: '{}'".format(src))
        return CompressReport([], [], [])

    compressed: List[Path] = []
    skipped: List[Path] = []
    errors: List[Tuple[Path, str]] = []

    progress = Progress(len(files), "Сжатие", enabled=show_progress)
    try:
        for path in files:
            target = dst if single_target else dst / (path.stem + suffix + ".mp4")

            # Не пережимаем, если результат новее исходника.
            if target.exists() and not overwrite:
                try:
                    if target.stat().st_mtime >= path.stat().st_mtime:
                        skipped.append(target)
                        progress.update(note=path.name)
                        continue
                except OSError:
                    pass

            target.parent.mkdir(parents=True, exist_ok=True)
            clip = None
            try:
                clip = VideoFileClip(str(path))
                clip.write_videofile(
                    str(target),
                    codec="libx264",
                    audio_codec="aac",
                    audio_bitrate=audio_bitrate,
                    preset=preset,
                    ffmpeg_params=["-crf", str(crf)],
                    logger=None,
                    remove_temp=True,
                )
                compressed.append(target)
            except Exception as exc:  # moviepy/ffmpeg бросают разные типы
                errors.append((path, str(exc)))
            finally:
                if clip is not None:
                    try:
                        clip.close()
                    except Exception:
                        pass
                progress.update(note=path.name)
    finally:
        progress.close()

    return CompressReport(compressed, skipped, errors)


# ---------------------------------------------------------------------------
# Склейка
# ---------------------------------------------------------------------------


def _collect_clips(
    source: Union[Path, Sequence[Path]], recursive: bool, exclude: Optional[Path]
) -> List[Path]:
    if isinstance(source, (str, bytes, os.PathLike)):
        path = Path(source)
        files = (
            [path]
            if path.is_file()
            else iter_files(path, recursive=recursive, suffixes=VIDEO_SUFFIXES)
        )
    else:
        files = [Path(p) for p in source]

    if exclude is not None:
        excluded = exclude.resolve()
        files = [p for p in files if p.resolve() != excluded]
    return sorted(files, key=lambda p: natural_key(p.name))


def merge_videos(
    source,
    output=None,
    fps: Optional[float] = None,
    recursive: bool = False,
    show_progress: bool = True,
) -> MergeReport:
    """Склеивает видео в один MP4 в естественном порядке имён.

    :param source: каталог, файл или список файлов
    :param fps: итоговый FPS; по умолчанию — максимальный FPS среди клипов
    """
    VideoFileClip = _video_clip_class()

    src = Path(source) if isinstance(source, (str, bytes, os.PathLike)) else Path(source[0])
    default_output = (
        src.parent / (src.name + "_merged.mp4") if src.is_file() else src / "merged.mp4"
    )
    target = Path(output) if output else default_output
    if target.suffix.lower() not in VIDEO_SUFFIXES:
        target = target.with_suffix(".mp4")

    files = _collect_clips(source, recursive, exclude=target)
    if not files:
        raise FileNotFoundError("Видеофайлы не найдены: '{}'".format(source))

    clips = []
    skipped: List[Path] = []
    progress = Progress(len(files), "Открытие", enabled=show_progress)
    try:
        for path in files:
            try:
                clips.append(VideoFileClip(str(path)))
            except Exception as exc:
                skipped.append(path)
                warn("Пропуск '{}': {}".format(path.name, exc))
            finally:
                progress.update(note=path.name)
    finally:
        progress.close()

    if not clips:
        raise RuntimeError("Ни один видеофайл не удалось открыть")

    total_duration = sum(float(clip.duration or 0) for clip in clips)
    info("Клипов: {}, длительность: {}".format(len(clips), format_duration(total_duration)))

    # Склейка методом compose допускает клипы разного размера.
    final = None
    try:
        from moviepy.editor import concatenate_videoclips
    except ImportError:  # moviepy >= 2
        from moviepy import concatenate_videoclips

    has_audio = all(clip.audio is not None for clip in clips)
    if not has_audio:
        clips = [clip.without_audio() for clip in clips]

    target_fps = fps
    if target_fps is None:
        detected = [float(clip.fps) for clip in clips if clip.fps]
        target_fps = min(max(detected), 60.0) if detected else 25.0

    try:
        final = concatenate_videoclips(clips, method="compose")
        if target.parent and not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(target),
            fps=float(target_fps),
            codec="libx264",
            audio_codec="aac" if has_audio else None,
            audio=has_audio,
            logger=None,
            remove_temp=True,
        )
    finally:
        if final is not None:
            try:
                final.close()
            except Exception:
                pass
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass

    return MergeReport(target, len(clips), total_duration, skipped)
