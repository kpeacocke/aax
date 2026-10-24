"""Run from the unpacked setuptools source before producing downstream RPMs."""

import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import unittest

from setuptools.command.egg_info import FileList, translate_pattern
import setuptools


class ManifestNormalizationTests(unittest.TestCase):
    def test_source_is_under_test(self) -> None:
        self.assertTrue(Path(setuptools.__file__).resolve().is_relative_to(Path.cwd()))

    def test_equivalent_patterns_and_paths(self) -> None:
        for pattern_form in ("NFC", "NFD"):
            for path_form in ("NFC", "NFD"):
                with self.subTest(pattern=pattern_form, path=path_form):
                    pattern = unicodedata.normalize(pattern_form, "caf\u00e9.txt")
                    path = unicodedata.normalize(path_form, "caf\u00e9.txt")
                    matcher = translate_pattern(pattern)
                    self.assertIsNotNone(matcher.match(path))
                    self.assertIsNotNone(matcher.search(path))
                    self.assertIsNone(matcher.match("public.txt"))

    def test_exclusion_directives(self) -> None:
        for form in ("NFC", "NFD"):
            secret = unicodedata.normalize(form, "caf\u00e9.txt")
            for directive, path in (
                ("exclude caf\u00e9.txt", secret),
                ("global-exclude caf\u00e9.txt", f"nested/{secret}"),
                ("recursive-exclude nested caf\u00e9.txt", f"nested/{secret}"),
                ("prune caf\u00e9", f"{secret[:-4]}/private.txt"),
            ):
                with self.subTest(form=form, directive=directive):
                    files = FileList()
                    files.files = ["public.py", path]
                    files.process_template_line(directive)
                    self.assertEqual(files.files, ["public.py"])

    def test_source_distribution_does_not_leak_excluded_file(self) -> None:
        source = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "setup.py").write_text(
                "from setuptools import setup\n"
                "setup(name='aax-regression', version='0', py_modules=['public'])\n"
            )
            (project / "public.py").write_text("VALUE = 1\n")
            (project / "cafe\u0301.txt").write_text("must not be distributed\n")
            (project / "MANIFEST.in").write_text(
                "global-include *.txt\nglobal-exclude caf\u00e9.txt\n", encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, "setup.py", "sdist"],
                cwd=project,
                env={**os.environ, "PYTHONPATH": str(source)},
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            archives = list((project / "dist").glob("*.tar.gz"))
            self.assertEqual(len(archives), 1)
            with tarfile.open(archives[0]) as archive:
                names = [unicodedata.normalize("NFC", name) for name in archive.getnames()]
            self.assertTrue(any(name.endswith("/public.py") for name in names))
            self.assertFalse(any(name.endswith("/caf\u00e9.txt") for name in names))


if __name__ == "__main__":
    unittest.main(verbosity=2)
