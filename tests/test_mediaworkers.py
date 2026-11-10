"""Тесты MediaWorkers: stdlib unittest, без внешних зависимостей."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mediaworkers.common import human_size, iter_files, natural_key, parse_name_list
from mediaworkers.files import (
    copy_by_names,
    count_files,
    delete_by_name,
    delete_duplicates,
    find_duplicate_groups,
    rename_files,
)


class CommonTests(unittest.TestCase):
    def test_natural_sort(self):
        names = ["file10", "file2", "file1"]
        self.assertEqual(sorted(names, key=natural_key), ["file1", "file2", "file10"])

    def test_parse_name_list(self):
        self.assertEqual(parse_name_list(["3", "1-2", "2"]), ["3", "1", "2"])
        self.assertEqual(parse_name_list(["1-3,7"]), ["1", "2", "3", "7"])

    def test_human_size(self):
        self.assertEqual(human_size(512), "512 Б")
        self.assertEqual(human_size(1536), "1.5 КБ")

    def test_iter_files_order_and_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a10.txt", "a2.txt", "a1.png"):
                (root / name).write_text(name, encoding="utf-8")
            names = [p.name for p in iter_files(root, suffixes={".txt"})]
            self.assertEqual(names, ["a2.txt", "a10.txt"])


class FilesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_count_files(self):
        (self.root / "one.txt").write_text("12345", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "two.png").write_bytes(b"x" * 10)

        result = count_files(self.root)
        self.assertEqual(result.files, 2)
        self.assertEqual(result.total_size, 15)
        self.assertEqual(result.by_extension[".png"][0], 1)

    def test_duplicates(self):
        (self.root / "photo (1).jpg").write_bytes(b"same")
        (self.root / "photo.jpg").write_bytes(b"same")
        (self.root / "other.jpg").write_bytes(b"different")

        groups = find_duplicate_groups(self.root, show_progress=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][0].name, "photo.jpg")  # хранитель — короткое имя

        report = delete_duplicates(self.root, show_progress=False)
        self.assertEqual(len(report.removed), 1)
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertFalse((self.root / "photo (1).jpg").exists())

    def test_copy_by_names(self):
        for number in (1, 2):
            (self.root / "IMG_{}.jpg".format(number)).write_bytes(b"x")
        (self.root / "IMG_3.jpg").write_bytes(b"x")
        dest = self.root / "dest"

        report = copy_by_names(self.root, dest, ["1", "3"], pattern="IMG_{id}.jpg")
        self.assertEqual(len(report.copied), 2)
        self.assertEqual({p.name for p in dest.iterdir()}, {"IMG_1.jpg", "IMG_3.jpg"})

    def test_delete_by_name_dry_run(self):
        (self.root / "voice_thumb.jpg").write_bytes(b"x")
        (self.root / "voice.jpg").write_bytes(b"x")

        report = delete_by_name(self.root, "thumb", dry_run=True)
        self.assertEqual(len(report.removed), 1)
        self.assertTrue((self.root / "voice_thumb.jpg").exists())

        delete_by_name(self.root, "thumb")
        self.assertFalse((self.root / "voice_thumb.jpg").exists())
        self.assertTrue((self.root / "voice.jpg").exists())

    def test_rename_in_place_with_cycle(self):
        for number in (1, 2, 3):
            (self.root / "{}.png".format(number)).write_bytes(
                "data-{}".format(number).encode()
            )

        report = rename_files(self.root, start=2, suffixes={".png"})
        self.assertEqual(len(report.renamed), 3)
        self.assertEqual(
            (self.root / "2.png").read_bytes(), b"data-1"
        )
        self.assertEqual(
            (self.root / "3.png").read_bytes(), b"data-2"
        )
        self.assertEqual(
            (self.root / "4.png").read_bytes(), b"data-3"
        )


if __name__ == "__main__":
    unittest.main()
