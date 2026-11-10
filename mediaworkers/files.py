"""Операции с файлами: подсчёт, копирование по именам, дубликаты, переименование.

Все функции возвращают отчёт, а не печатают результат: вывод остаётся
ответственностью CLI, кроме необязательного прогресса.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

from .common import (
    Progress,
    ensure_dir,
    info,
    iter_files,
    natural_key,
    warn,
)

__all__ = [
    "CopyReport",
    "CountResult",
    "DuplicateReport",
    "RenameReport",
    "count_files",
    "copy_by_names",
    "delete_by_name",
    "delete_duplicates",
    "file_digest",
    "find_duplicate_groups",
    "rename_files",
]

_HASH_CHUNK = 1024 * 1024


# ---------------------------------------------------------------------------
# Подсчёт
# ---------------------------------------------------------------------------


class CountResult(NamedTuple):
    files: int
    total_size: int
    by_extension: Dict[str, Tuple[int, int]]
    elapsed: float


def count_files(directory, recursive: bool = True) -> CountResult:
    """Считает количество и суммарный размер файлов (быстрый обход scandir)."""
    import time

    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError("Каталог не найден: {}".format(root))

    started = time.perf_counter()
    files = 0
    total_size = 0
    by_extension: Dict[str, Tuple[int, int]] = {}

    stack: List[str] = [str(root)]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            warn("Нет доступа к '{}': {}".format(current, exc))
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    if recursive:
                        stack.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    files += 1
                    size = entry.stat(follow_symlinks=False).st_size
                    total_size += size
                    suffix = Path(entry.name).suffix.lower() or "<без расширения>"
                    count, ext_size = by_extension.get(suffix, (0, 0))
                    by_extension[suffix] = (count + 1, ext_size + size)
            except OSError:
                continue

    return CountResult(files, total_size, by_extension, time.perf_counter() - started)


# ---------------------------------------------------------------------------
# Дубликаты
# ---------------------------------------------------------------------------


def file_digest(path, chunk_size: int = _HASH_CHUNK) -> str:
    """BLAKE2b-хеш файла: быстрее и компактнее, чем читать файл целиком."""
    digest = hashlib.blake2b(digest_size=16)
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicate_groups(
    directory,
    recursive: bool = False,
    min_size: int = 0,
    show_progress: bool = True,
) -> List[List[Path]]:
    """Ищет группы идентичных файлов.

    Сначала файлы группируются по размеру, и только совпавшие по размеру
    хешируются — это избавляет от чтения уникальных файлов.
    """
    if min_size < 0:
        raise ValueError("min_size не может быть отрицательным")

    sizes: Dict[int, List[Path]] = defaultdict(list)
    for path in iter_files(directory, recursive=recursive):
        try:
            size = path.stat().st_size
        except OSError as exc:
            warn("Не удалось прочитать '{}': {}".format(path, exc))
            continue
        if size >= min_size:
            sizes[size].append(path)

    candidates = {size: paths for size, paths in sizes.items() if len(paths) > 1}
    to_hash = sum(len(paths) for paths in candidates.values())

    groups: List[List[Path]] = []
    progress = Progress(to_hash, "Хеширование", enabled=show_progress and to_hash > 0)
    try:
        for size in sorted(candidates):
            buckets: Dict[str, List[Path]] = defaultdict(list)
            for path in candidates[size]:
                try:
                    buckets[file_digest(path)].append(path)
                except OSError as exc:
                    warn("Не удалось прочитать '{}': {}".format(path, exc))
                finally:
                    progress.update(note=path.name)
            for identical in buckets.values():
                if len(identical) > 1:
                    # Хранитель — файл с самым коротким именем: обычно это
                    # исходник, а не копия вида "photo (1).jpg".
                    groups.append(
                        sorted(
                            identical,
                            key=lambda p: (len(p.name), natural_key(p.name)),
                        )
                    )
    finally:
        progress.close()

    groups.sort(key=lambda group: natural_key(group[0].name))
    return groups


class DuplicateReport(NamedTuple):
    groups: int
    removed: List[Path]
    freed: int
    errors: List[Tuple[Path, str]]


def delete_duplicates(
    directory,
    recursive: bool = False,
    dry_run: bool = False,
    min_size: int = 0,
    show_progress: bool = True,
) -> DuplicateReport:
    """Удаляет дубликаты, оставляя первый файл в каждой группе."""
    groups = find_duplicate_groups(
        directory, recursive=recursive, min_size=min_size, show_progress=show_progress
    )

    removed: List[Path] = []
    errors: List[Tuple[Path, str]] = []
    freed = 0

    for group in groups:
        keeper = group[0]
        info("  оставляю: {}".format(keeper))
        for duplicate in group[1:]:
            info("  дубликат: {}".format(duplicate))
            if dry_run:
                removed.append(duplicate)
                try:
                    freed += duplicate.stat().st_size
                except OSError:
                    pass
                continue
            try:
                size = duplicate.stat().st_size
                os.remove(str(duplicate))
                removed.append(duplicate)
                freed += size
            except OSError as exc:
                errors.append((duplicate, str(exc)))

    return DuplicateReport(len(groups), removed, freed, errors)


# ---------------------------------------------------------------------------
# Копирование / перемещение по именам
# ---------------------------------------------------------------------------


class CopyReport(NamedTuple):
    copied: List[Path]
    missing: List[str]
    skipped: List[Path]
    errors: List[Tuple[str, str]]


def copy_by_names(
    source,
    destination,
    names: Sequence[str],
    pattern: str = "IMG_{id}.jpg",
    move: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
) -> CopyReport:
    """Копирует (или перемещает) файлы, имена которых собраны из id.

    :param pattern: шаблон имени, например ``IMG_{id}.jpg`` или ``{id}.png``
    """
    src = Path(source)
    dst = Path(destination)
    if not src.is_dir():
        raise NotADirectoryError("Каталог не найден: {}".format(src))

    wanted: Dict[str, str] = {}
    for name in names:
        wanted[pattern.format(id=name, name=name)] = name

    available: Dict[str, Path] = {}
    with os.scandir(str(src)) as entries:
        for entry in entries:
            if entry.is_file(follow_symlinks=False):
                available[entry.name] = Path(entry.path)
    available_lower = {key.lower(): value for key, value in available.items()}

    if not dry_run:
        ensure_dir(dst)

    copied: List[Path] = []
    missing: List[str] = []
    skipped: List[Path] = []
    errors: List[Tuple[str, str]] = []

    for filename, name in wanted.items():
        path = available.get(filename) or available_lower.get(filename.lower())
        if path is None:
            missing.append(filename)
            continue

        target = dst / path.name
        if target.exists() and not overwrite:
            skipped.append(target)
            continue
        if dry_run:
            copied.append(target)
            continue

        try:
            if move:
                shutil.move(str(path), str(target))
            else:
                shutil.copy2(str(path), str(target))
            copied.append(target)
        except OSError as exc:
            errors.append((filename, str(exc)))

    return CopyReport(copied, missing, skipped, errors)


# ---------------------------------------------------------------------------
# Удаление по имени
# ---------------------------------------------------------------------------


class DeleteReport(NamedTuple):
    removed: List[Path]
    freed: int
    errors: List[Tuple[Path, str]]


def delete_by_name(
    directory,
    substring: str,
    recursive: bool = False,
    ignore_case: bool = True,
    dry_run: bool = False,
) -> DeleteReport:
    """Удаляет файлы, в имени которых есть подстрока."""
    needle = substring.lower() if ignore_case else substring
    removed: List[Path] = []
    errors: List[Tuple[Path, str]] = []
    freed = 0

    for path in iter_files(directory, recursive=recursive):
        haystack = path.name.lower() if ignore_case else path.name
        if needle not in haystack:
            continue
        if dry_run:
            removed.append(path)
            try:
                freed += path.stat().st_size
            except OSError:
                pass
            continue
        try:
            size = path.stat().st_size
            os.remove(str(path))
            removed.append(path)
            freed += size
        except OSError as exc:
            errors.append((path, str(exc)))

    return DeleteReport(removed, freed, errors)


# ---------------------------------------------------------------------------
# Переименование
# ---------------------------------------------------------------------------


class RenameReport(NamedTuple):
    renamed: List[Tuple[Path, Path]]
    skipped: List[Path]
    errors: List[Tuple[Path, str]]


def rename_files(
    source,
    destination=None,
    start: int = 1,
    pattern: str = "{n}{ext}",
    suffixes: Optional[Iterable[str]] = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> RenameReport:
    """Переименовывает файлы по шаблону в естественном порядке.

    Поддерживаемые поля шаблона: ``{n}`` — номер, ``{name}`` — исходное имя
    без расширения, ``{ext}`` — расширение вместе с точкой.

    При переименовании внутри одного каталога файлы сначала уводятся во
    временные имена, поэтому циклические замены (1 -> 2, 2 -> 3) безопасны.
    """
    src = Path(source).resolve()
    dst = Path(destination).resolve() if destination else src
    files = iter_files(src, recursive=False, suffixes=suffixes)

    if not dry_run:
        ensure_dir(dst)

    source_paths = {path.resolve() for path in files}
    plan: List[Tuple[Path, Path]] = []
    skipped: List[Path] = []
    errors: List[Tuple[Path, str]] = []
    planned_targets = set()

    for offset, path in enumerate(files):
        new_name = pattern.format(n=start + offset, name=path.stem, ext=path.suffix)
        target = dst / new_name

        if target == path:
            skipped.append(path)
            continue
        if target in planned_targets:
            errors.append((path, "шаблон даёт неуникальное имя: {}".format(new_name)))
            continue
        if target.exists() and not overwrite and target.resolve() not in source_paths:
            skipped.append(target)
            warn("Пропуск: '{}' уже существует".format(target))
            continue
        planned_targets.add(target)
        plan.append((path, target))

    renamed: List[Tuple[Path, Path]] = []
    if dry_run:
        return RenameReport(plan, skipped, errors)

    same_directory = dst.resolve() == src.resolve()
    staged: List[Tuple[Path, Path, Path]] = []

    for index, (path, target) in enumerate(plan):
        if same_directory:
            temporary = path.with_name(".mw_tmp_{}{}".format(index, path.suffix))
            try:
                path.rename(temporary)
            except OSError as exc:
                errors.append((path, str(exc)))
                continue
            staged.append((temporary, target, path))
        else:
            try:
                if target.exists() and overwrite:
                    os.replace(str(path), str(target))
                else:
                    path.rename(target)
                renamed.append((path, target))
            except OSError as exc:
                errors.append((path, str(exc)))

    for temporary, target, original in staged:
        try:
            if target.exists() and overwrite:
                os.replace(str(temporary), str(target))
            else:
                temporary.rename(target)
            renamed.append((original, target))
        except OSError as exc:
            errors.append((original, str(exc)))
            try:
                temporary.rename(original)
            except OSError:
                errors.append((temporary, "не удалось вернуть исходное имя"))

    return RenameReport(renamed, skipped, errors)
