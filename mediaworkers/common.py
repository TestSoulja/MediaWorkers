"""Общие помощники: вывод, прогресс, поиск файлов, разбор списков.

Модуль не зависит от тяжёлых библиотек и работает на Python 3.7+.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional

IMAGE_SUFFIXES = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
)
VIDEO_SUFFIXES = frozenset(
    {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".m4v", ".mpg", ".mpeg"}
)

__all__ = [
    "IMAGE_SUFFIXES",
    "VIDEO_SUFFIXES",
    "Progress",
    "ensure_dir",
    "error",
    "format_duration",
    "human_size",
    "info",
    "is_under",
    "iter_files",
    "natural_key",
    "parse_name_list",
    "read_list_file",
    "require",
    "success",
    "warn",
]

# ---------------------------------------------------------------------------
# Цветной вывод
# ---------------------------------------------------------------------------

_NO_COLOR = bool(os.environ.get("NO_COLOR"))

try:  # colorama делает ANSI-коды совместимыми со старым консольным хостом Windows
    import colorama as _colorama

    _colorama.init(strip=_NO_COLOR or not sys.stdout.isatty())
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"
except ImportError:  # pragma: no cover - зависит от окружения
    if _NO_COLOR or os.name == "nt":
        RED = GREEN = YELLOW = CYAN = MAGENTA = RESET = ""
    else:
        RED, GREEN, YELLOW, CYAN, MAGENTA = (
            "\033[31m",
            "\033[32m",
            "\033[33m",
            "\033[36m",
            "\033[35m",
        )
        RESET = "\033[0m"


def _with_color(text: str, color: str) -> str:
    return "{}{}{}".format(color, text, RESET) if color else text


def info(message: str) -> None:
    print(message)


def success(message: str) -> None:
    print(_with_color(message, GREEN))


def warn(message: str) -> None:
    print(_with_color(message, YELLOW))


def error(message: str) -> None:
    print(_with_color(message, RED), file=sys.stderr)


# ---------------------------------------------------------------------------
# Форматирование
# ---------------------------------------------------------------------------

_UNITS = ("Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ")


def human_size(size: float) -> str:
    """Человекочитаемый размер: 1536 -> '1.5 КБ'."""
    size = float(size)
    for unit in _UNITS:
        if size < 1024.0 or unit == _UNITS[-1]:
            return "{:.1f} {}".format(size, unit) if unit != "Б" else "{:.0f} Б".format(size)
        size /= 1024.0
    return "{:.1f} ПБ".format(size)  # pragma: no cover


def format_duration(seconds: Optional[float]) -> str:
    """Секунды -> 'ЧЧ:ММ:СС'."""
    total = int(round(seconds or 0))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, secs)


# ---------------------------------------------------------------------------
# Прогресс
# ---------------------------------------------------------------------------


class Progress:
    """Простой индикатор прогресса с троттлингом.

    В интерактивном терминале перерисовывает одну строку, иначе печатает
    только итоговый результат — логи остаются чистыми.
    """

    def __init__(
        self,
        total: int,
        label: str = "",
        stream=None,
        min_interval: float = 0.08,
        enabled: bool = True,
    ) -> None:
        self.total = max(int(total), 1)
        self.label = label
        self.done = 0
        self._stream = stream or sys.stdout
        self._interactive = bool(getattr(self._stream, "isatty", lambda: False)())
        self._min_interval = min_interval
        self._last_draw = 0.0
        self._finished = False
        if not enabled:
            self._finished = True

    def __enter__(self) -> "Progress":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def update(self, step: int = 1, note: str = "") -> None:
        if self._finished:
            return
        self.done = min(self.done + step, self.total)
        now = time.monotonic()
        if self.done < self.total:
            if not self._interactive or now - self._last_draw < self._min_interval:
                return
        self._draw(note, final=self.done >= self.total)

    def _draw(self, note: str = "", final: bool = False) -> None:
        self._last_draw = time.monotonic()
        percent = 100.0 * self.done / self.total
        prefix = "{} ".format(self.label) if self.label else ""
        line = "{prefix}[{done}/{total}] {percent:5.1f}%".format(
            prefix=prefix, done=self.done, total=self.total, percent=percent
        )
        if note:
            line += "  " + note
        if self._interactive:
            end = "\n" if final else ""
            self._stream.write("\r" + line + end)
        elif final:
            self._stream.write(line + "\n")
        self._stream.flush()
        if final:
            self._finished = True

    def close(self, note: str = "") -> None:
        if self._finished:
            return
        self._finished = True
        self.done = self.total
        self._draw(note, final=True)


# ---------------------------------------------------------------------------
# Файловая система
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"(\d+)")


def natural_key(value) -> List[object]:
    """Ключ «естественной» сортировки: file2 < file10."""
    return [int(part) if part.isdigit() else part.lower() for part in _NUMBER_RE.split(str(value))]


def ensure_dir(path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _suffix_allowed(path: Path, suffixes: Optional[Iterable[str]]) -> bool:
    return suffixes is None or path.suffix.lower() in suffixes


def is_under(path, parent) -> bool:
    """True, если path находится внутри parent (или совпадает с ним)."""
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def iter_files(
    directory,
    recursive: bool = False,
    suffixes: Optional[Iterable[str]] = None,
    ignore_hidden: bool = False,
) -> List[Path]:
    """Список файлов каталога в естественном порядке.

    :param directory: исходный каталог
    :param recursive: обходить вложенные каталоги
    :param suffixes: набор допустимых расширений (в нижнем регистре)
    :param ignore_hidden: пропускать файлы, начинающиеся с точки
    """
    root = Path(directory).resolve()
    if not root.is_dir():
        raise NotADirectoryError("Каталог не найден: {}".format(root))

    allowed = {s.lower() for s in suffixes} if suffixes is not None else None
    result: List[Path] = []

    if recursive:
        for dirpath, dirnames, filenames in os.walk(str(root)):
            dirnames[:] = sorted(
                (d for d in dirnames if not (ignore_hidden and d.startswith("."))),
                key=natural_key,
            )
            for name in filenames:
                if ignore_hidden and name.startswith("."):
                    continue
                path = Path(dirpath) / name
                if _suffix_allowed(path, allowed):
                    result.append(path)
        result.sort(key=lambda p: natural_key(str(p.relative_to(root))))
    else:
        with os.scandir(str(root)) as entries:
            for entry in entries:
                if ignore_hidden and entry.name.startswith("."):
                    continue
                if entry.is_file(follow_symlinks=False):
                    path = Path(entry.path)
                    if _suffix_allowed(path, allowed):
                        result.append(path)
        result.sort(key=lambda p: natural_key(p.name))

    return result


# ---------------------------------------------------------------------------
# Списки: id/имена и файлы со ссылками
# ---------------------------------------------------------------------------

_RANGE_RE = re.compile(r"^(\d+)\s*[-:]\s*(\d+)$")


def parse_name_list(tokens: Iterable[str]) -> List[str]:
    """Разворачивает диапазоны: '7598-7600' -> ['7598', '7599', '7600'].

    Поддерживаются также списки через запятую ('1-3,7') и смешанные наборы.
    Дубликаты удаляются, исходный порядок сохраняется.
    """
    result: List[str] = []
    seen = set()

    def add(value: str) -> None:
        if value not in seen:
            seen.add(value)
            result.append(value)

    def add_token(token: str) -> None:
        token = token.strip()
        if not token:
            return
        match = _RANGE_RE.match(token)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            if end < start:
                start, end = end, start
            for value in range(start, end + 1):
                add(str(value))
        else:
            add(token)

    for token in tokens:
        for part in str(token).split(","):
            add_token(part)
    return result


def read_list_file(path) -> List[str]:
    """Читает список строк, игнорируя пустые строки и комментарии (#, //)."""
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - маловероятно
        raise ValueError("Не удалось определить кодировку файла: {}".format(path))

    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        items.append(line)
    return items


# ---------------------------------------------------------------------------
# Зависимости
# ---------------------------------------------------------------------------


def require(module_name: str, package: Optional[str] = None):
    """Импортирует модуль или бросает ImportError с подсказкой по установке."""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        package = package or module_name
        raise ImportError(
            "Не найден модуль '{module}'. Установите зависимость: pip install {package}".format(
                module=module_name, package=package
            )
        ) from exc
