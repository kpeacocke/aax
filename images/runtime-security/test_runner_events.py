"""Exercise the actual Runner.run directory boundary without launching a job."""

import errno
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ansible_runner.runner import Runner


class CommandBoundaryReached(Exception):
    pass


class RunnerEventDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.artifacts = Path(self.temporary.name) / "artifacts"
        self.events = self.artifacts / "job_events"
        self.runner = Runner(SimpleNamespace(
            artifact_dir=str(self.artifacts), ident=None, command=["unused"],
            env={}, cwd=self.temporary.name,
        ))

    def run_to_command_boundary(self):
        with patch("ansible_runner.runner.os.chmod", side_effect=CommandBoundaryReached):
            with self.assertRaises(CommandBoundaryReached):
                self.runner.run()

    def test_new_directory_is_private(self):
        self.run_to_command_boundary()
        self.assertTrue(self.events.is_dir())
        self.assertEqual(self.events.stat().st_mode & 0o777, 0o700)

    def test_existing_directory_and_events_are_preserved(self):
        self.events.mkdir(parents=True, mode=0o700)
        self.events.chmod(0o750)
        event = self.events / "existing.json"
        event.write_text('{"event": "preserved"}')
        self.run_to_command_boundary()
        self.assertEqual(event.read_text(), '{"event": "preserved"}')
        self.assertEqual(self.events.stat().st_mode & 0o777, 0o750)

    def test_concurrent_creator_does_not_abort_runner(self):
        original_mkdir = os.mkdir
        injected = False

        def racing_mkdir(path, mode=0o777, *, dir_fd=None):
            nonlocal injected
            if Path(path) == self.events and not injected:
                injected = True
                original_mkdir(path, mode, dir_fd=dir_fd)
            return original_mkdir(path, mode, dir_fd=dir_fd)

        with patch("ansible_runner.runner.os.mkdir", side_effect=racing_mkdir):
            self.run_to_command_boundary()
        self.assertTrue(injected)
        self.assertEqual(self.events.stat().st_mode & 0o777, 0o700)

    def test_existing_file_is_not_accepted_as_a_directory(self):
        self.artifacts.mkdir()
        self.events.write_text("not a directory")
        with self.assertRaises(FileExistsError):
            self.runner.run()
        self.assertEqual(self.events.read_text(), "not a directory")

    def test_permission_errors_still_abort_runner(self):
        original_mkdir = os.mkdir

        def denied_mkdir(path, mode=0o777, *, dir_fd=None):
            if Path(path) == self.events:
                raise PermissionError(errno.EACCES, "permission denied", path)
            return original_mkdir(path, mode, dir_fd=dir_fd)

        with patch("ansible_runner.runner.os.mkdir", side_effect=denied_mkdir):
            with self.assertRaises(PermissionError):
                self.runner.run()


if __name__ == "__main__":
    unittest.main()
