"""Изображения: пакетное изменение размера и рендер PDF в PNG."""

from __future__ import annotations

from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence, Tuple

from .common import (
    IMAGE_SUFFIXES,
    Progress,
    ensure_dir,
    is_under,
    iter_files,
    require,
    warn,
)

__all__ = ["PdfReport", "ResizeReport", "pdf_to_png", "resize_images"]

_JPEG_QUALITY = 95


class ResizeReport(NamedTuple):
    resized: List[Path]
    skipped: List[Path]
    errors: List[Tuple[Path, str]]


def _resampling():
    """LANCZOS-фильтр, совместимый с Pillow 9 и 10+."""
    from PIL import Image

    return getattr(getattr(Image, "Resampling", Image), "LANCZOS")


def _prepare_for_jpeg(image):
    """Убирает альфа-канал, подмешивая прозрачность в белый фон."""
    from PIL import Image

    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if image.mode not in ("RGB", "L"):
        return image.convert("RGB")
    return image


def _save_image(image, target: Path, quality: int) -> None:
    suffix = target.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        _prepare_for_jpeg(image).save(
            str(target), quality=quality, subsampling=0, optimize=True
        )
    elif suffix == ".png":
        image.save(str(target), optimize=True)
    elif suffix == ".webp":
        image.save(str(target), quality=quality, method=6)
    else:
        image.save(str(target))


def resize_images(
    source,
    destination=None,
    size: Tuple[int, int] = (64, 64),
    keep_aspect: bool = False,
    quality: int = _JPEG_QUALITY,
    recursive: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
    show_progress: bool = True,
) -> ResizeReport:
    """Изменяет размер всех изображений каталога.

    :param destination: каталог результата; по умолчанию — исходный каталог
    :param size: (ширина, высота) в пикселях
    :param keep_aspect: сохранять пропорции (вписывать в рамку size)
    :param overwrite: перезаписывать существующие файлы
    """
    Image = require("PIL.Image", "Pillow")
    ImageOps = require("PIL.ImageOps", "Pillow")

    width, height = int(size[0]), int(size[1])
    if width <= 0 or height <= 0:
        raise ValueError("Размер должен быть положительным: {}x{}".format(width, height))

    src = Path(source).resolve()
    dst = Path(destination).resolve() if destination else src
    files = iter_files(src, recursive=recursive, suffixes=IMAGE_SUFFIXES)
    if dst != src:
        # Не обрабатываем собственные результаты при повторном запуске.
        files = [path for path in files if not is_under(path, dst)]
    if not files:
        warn("В '{}' нет изображений".format(src))
        return ResizeReport([], [], [])

    resized: List[Path] = []
    skipped: List[Path] = []
    errors: List[Tuple[Path, str]] = []
    created_dirs = set()
    resampling = _resampling()

    progress = Progress(len(files), "Ресайз", enabled=show_progress)
    try:
        for path in files:
            relative = path.relative_to(src) if recursive else Path(path.name)
            target = dst / relative

            if target.exists() and not overwrite:
                skipped.append(target)
                progress.update(note=path.name)
                continue

            if dry_run:
                resized.append(target)
                progress.update(note=path.name)
                continue

            try:
                parent = target.parent
                if parent not in created_dirs:
                    ensure_dir(parent)
                    created_dirs.add(parent)

                with Image.open(str(path)) as opened:
                    image = ImageOps.exif_transpose(opened)
                    if keep_aspect:
                        image.thumbnail((width, height), resampling)
                    else:
                        image = image.resize((width, height), resampling)
                    _save_image(image, target, quality)
                resized.append(target)
            except (OSError, ValueError) as exc:
                errors.append((path, str(exc)))
            finally:
                progress.update(note=path.name)
    finally:
        progress.close()

    return ResizeReport(resized, skipped, errors)


# ---------------------------------------------------------------------------
# PDF -> PNG
# ---------------------------------------------------------------------------


class PdfReport(NamedTuple):
    created: List[Path]
    errors: List[Tuple[Path, str]]


def _parse_pages(spec: Optional[str]) -> Optional[List[int]]:
    """'ALL' -> None, '1-3,5' -> [1, 2, 3, 5]."""
    if spec is None or str(spec).strip().upper() == "ALL":
        return None

    pages: List[int] = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start, end = int(left), int(right)
            step = 1 if end >= start else -1
            pages.extend(range(start, end + step, step))
        else:
            pages.append(int(part))
    if not pages:
        raise ValueError("Пустой список страниц: '{}'".format(spec))
    return sorted(set(pages))


def _pdf_to_png_pdf2image(
    pdf_path: Path, output_dir: Path, pages: Optional[Sequence[int]], dpi: int
) -> List[Path]:
    convert_from_path = require("pdf2image").convert_from_path
    created: List[Path] = []

    if pages is None:
        images = convert_from_path(str(pdf_path), dpi=dpi)
        for index, image in enumerate(images, start=1):
            target = output_dir / "{}_p{:03d}.png".format(pdf_path.stem, index)
            image.save(str(target), "PNG")
            created.append(target)
        return created

    for page in pages:
        images = convert_from_path(
            str(pdf_path), dpi=dpi, first_page=page, last_page=page
        )
        if not images:
            warn("Страница {} не найдена в '{}'".format(page, pdf_path.name))
            continue
        target = output_dir / "{}_p{:03d}.png".format(pdf_path.stem, page)
        images[0].save(str(target), "PNG")
        created.append(target)
    return created


def _pdf_to_png_pdf2jpg(
    pdf_path: Path, output_dir: Path, page_spec: str
) -> List[Path]:
    """Резервный backend: пакет pdf2jpg (использует свой формат имён)."""
    pdf2jpg = require("pdf2jpg")
    before = set(output_dir.rglob("*.png")) if output_dir.exists() else set()
    pdf2jpg.convert_pdf2jpg(str(pdf_path), str(output_dir), pages=page_spec)
    after = set(output_dir.rglob("*.png")) if output_dir.exists() else set()
    return sorted(after - before, key=lambda p: str(p))


def pdf_to_png(
    source,
    destination=None,
    pages: Optional[str] = "ALL",
    dpi: int = 200,
) -> PdfReport:
    """Рендерит PDF (файл или каталог с PDF) в PNG-страницы."""
    src = Path(source).resolve()
    if not src.exists():
        raise FileNotFoundError("Путь не найден: {}".format(src))
    if src.is_file() and src.suffix.lower() != ".pdf":
        raise ValueError("Ожидается PDF-файл: {}".format(src))

    pdf_files = [src] if src.is_file() else iter_files(src, suffixes={".pdf"})
    if not pdf_files:
        warn("PDF-файлы не найдены: '{}'".format(src))
        return PdfReport([], [])

    output_dir = Path(destination) if destination else (
        src.parent / (src.stem + "_png") if src.is_file() else src / "png"
    )
    ensure_dir(output_dir)

    page_list = _parse_pages(pages)
    created: List[Path] = []
    errors: List[Tuple[Path, str]] = []

    for pdf_path in pdf_files:
        if pdf_path.suffix.lower() != ".pdf":
            continue
        try:
            try:
                created.extend(
                    _pdf_to_png_pdf2image(pdf_path, output_dir, page_list, dpi)
                )
            except ImportError:
                created.extend(
                    _pdf_to_png_pdf2jpg(
                        pdf_path, output_dir, "ALL" if page_list is None else pages
                    )
                )
        except Exception as exc:  # backend-ошибки разнородны, но не должны ронять пачку
            errors.append((pdf_path, str(exc)))

    return PdfReport(created, errors)
