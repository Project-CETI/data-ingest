"""Offline command-completion regressions for issue #42.

Run with: python -m unittest discover -s tests -p test_whaletag_cleanup.py -v
All tag discovery, preflight checks, and SSH operations use in-memory doubles.
Socket connections are blocked, so no tag or AWS access is possible.
"""

import __future__
import importlib.util
import io
from pathlib import Path
import socket
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock


class CleanupTests(unittest.TestCase):
    def setUp(self):
        for name in ("connect", "connect_ex"):
            patcher = mock.patch.object(
                socket.socket, name,
                side_effect=AssertionError("Network access is forbidden"),
            )
            patcher.start()
            self.addCleanup(patcher.stop)

        dependencies = {
            name: mock.Mock(name=name)
            for name in ("paramiko", "findssh", "netifaces", "ceti.utils")
        }
        path = Path(__file__).resolve().parents[1] / "ceti" / "whaletag.py"
        spec = importlib.util.spec_from_file_location("offline_whaletag", path)
        self.tag = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, dependencies):
            # Defer the existing discovery annotation on Python 3.7-3.9.
            # This isolates cleanup tests, not production import compatibility.
            code = compile(path.read_bytes(), str(path), "exec",
                           flags=__future__.annotations.compiler_flag,
                           dont_inherit=True)
            exec(code, self.tag.__dict__)

        self.tag.can_connect = mock.Mock(return_value=True)
        self.tag.stop_capture_service = mock.Mock()
        self.tag.create_filelist_to_download = mock.Mock(return_value=[])
        self.ssh = self.tag.paramiko.SSHClient.return_value
        self.stdout = mock.Mock()
        self.stderr = mock.Mock()
        self.stdout.read.return_value = b""
        self.channel = self.stdout.channel
        self.channel.recv_exit_status.return_value = 0
        self.ssh.exec_command.return_value = (None, self.stdout, self.stderr)

        self.events = mock.Mock()
        for operation, name in (
            (self.ssh.exec_command, "execute"),
            (self.channel.set_combine_stderr, "combine"),
            (self.stdout.read, "read"),
            (self.channel.recv_exit_status, "status"),
            (self.ssh.close, "close"),
        ):
            self.events.attach_mock(operation, name)
        self.output = io.StringIO()
        redirect = redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def clean(self):
        return self.tag.clean_tag("wt-offline")

    def assert_no_success(self):
        self.assertNotIn("Data erased successfully", self.output.getvalue())

    def test_success_drains_output_and_waits_before_closing(self):
        self.assertIsNone(self.clean())
        self.assertEqual(self.events.mock_calls, [
            mock.call.execute("sudo rm -rf /data/*.*"),
            mock.call.combine(True),
            mock.call.read(),
            mock.call.status(),
            mock.call.close(),
        ])
        self.tag.can_connect.assert_called_once_with("wt-offline")
        self.tag.stop_capture_service.assert_called_once_with("wt-offline")
        self.tag.create_filelist_to_download.assert_called_once_with(
            "wt-offline")
        self.ssh.connect.assert_called_once_with(
            "wt-offline", username=self.tag.DEFAULT_USERNAME,
            password=self.tag.DEFAULT_PASSWORD,
        )
        self.assertIn("Data erased successfully", self.output.getvalue())
        # Combining avoids filling one stream's window while sequentially
        # reading the other stream to EOF.
        self.stderr.read.assert_not_called()

    def test_success_is_not_reported_until_status_is_known(self):
        def read():
            self.channel.set_combine_stderr.assert_called_once_with(True)
            self.channel.recv_exit_status.assert_not_called()
            self.ssh.close.assert_not_called()
            self.assert_no_success()
            return b""

        def status():
            self.stdout.read.assert_called_once_with()
            self.ssh.close.assert_not_called()
            self.assert_no_success()
            return 0

        self.stdout.read.side_effect = read
        self.channel.recv_exit_status.side_effect = status
        self.clean()
        self.assertIn("Data erased successfully", self.output.getvalue())

    def test_nonzero_status_reports_remote_diagnostic_and_closes(self):
        self.stdout.read.return_value = b"rm: Permission denied\n"
        for status in (1, 126, 127, 255):
            with self.subTest(status=status):
                self.channel.recv_exit_status.return_value = status
                with self.assertRaises(RuntimeError) as caught:
                    self.clean()
                self.assertIn("wt-offline", str(caught.exception))
                self.assertIn(f"exit status {status}", str(caught.exception))
                self.assertIn("rm: Permission denied", str(caught.exception))
                self.assert_no_success()
                self.ssh.close.assert_called_once_with()
                self.ssh.close.reset_mock()

    def test_missing_exit_status_is_not_success(self):
        self.channel.recv_exit_status.return_value = -1
        with self.assertRaisesRegex(RuntimeError, "exit status -1"):
            self.clean()
        self.assert_no_success()
        self.ssh.close.assert_called_once_with()

    def test_failure_without_diagnostic_still_reports_status(self):
        self.channel.recv_exit_status.return_value = 1
        for output in (b"", b" \n\t"):
            with self.subTest(output=output):
                self.stdout.read.return_value = output
                with self.assertRaisesRegex(
                        RuntimeError, "exit status 1.*no error output"):
                    self.clean()
                self.assert_no_success()

    def test_non_utf8_diagnostic_does_not_hide_remote_failure(self):
        self.stdout.read.return_value = b"rm: \xff disk error\n"
        self.channel.recv_exit_status.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "disk error"):
            self.clean()
        self.assert_no_success()
        self.ssh.close.assert_called_once_with()

    def test_zero_status_allows_remote_output(self):
        self.stdout.read.return_value = b"sudo: informational message\n"
        self.clean()
        self.assertIn("Data erased successfully", self.output.getvalue())

    def test_command_setup_failure_is_not_success(self):
        error = OSError("command rejected")
        self.ssh.exec_command.side_effect = error
        with self.assertRaises(OSError) as caught:
            self.clean()
        self.assertIs(caught.exception, error)
        self.channel.recv_exit_status.assert_not_called()
        self.assert_no_success()
        self.ssh.close.assert_called_once_with()

    def test_output_or_status_failure_closes_and_propagates(self):
        for operation in (self.channel.set_combine_stderr, self.stdout.read,
                          self.channel.recv_exit_status):
            with self.subTest(operation=operation):
                error = OSError("connection lost")
                operation.side_effect = error
                with self.assertRaises(OSError) as caught:
                    self.clean()
                self.assertIs(caught.exception, error)
                self.assert_no_success()
                self.ssh.close.assert_called_once_with()
                operation.side_effect = None
                self.ssh.close.reset_mock()

    def test_interruption_does_not_report_success(self):
        for operation in (self.stdout.read, self.channel.recv_exit_status):
            with self.subTest(operation=operation):
                operation.side_effect = KeyboardInterrupt()
                with self.assertRaises(KeyboardInterrupt):
                    self.clean()
                self.assert_no_success()
                self.ssh.close.assert_called_once_with()
                operation.side_effect = None
                self.ssh.close.reset_mock()

    def test_unreachable_tag_does_not_run_preflight_or_deletion(self):
        self.tag.can_connect.return_value = False
        self.clean()
        self.tag.stop_capture_service.assert_not_called()
        self.tag.create_filelist_to_download.assert_not_called()
        self.tag.paramiko.SSHClient.assert_not_called()
        self.assert_no_success()

    def test_undownloaded_files_prevent_deletion(self):
        self.tag.create_filelist_to_download.return_value = ["/data/new.raw"]
        self.clean()
        self.tag.paramiko.SSHClient.assert_not_called()
        self.assert_no_success()

    def test_preflight_failure_prevents_deletion(self):
        for operation in (self.tag.stop_capture_service,
                          self.tag.create_filelist_to_download):
            with self.subTest(operation=operation):
                error = OSError("preflight failed")
                operation.side_effect = error
                with self.assertRaises(OSError) as caught:
                    self.clean()
                self.assertIs(caught.exception, error)
                self.tag.paramiko.SSHClient.assert_not_called()
                self.assert_no_success()
                operation.side_effect = None


if __name__ == "__main__":
    unittest.main()
