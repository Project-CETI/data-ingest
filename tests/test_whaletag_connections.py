"""Offline connection-lifetime regressions for issue #41.

Load the real whaletag module with isolated dependency doubles so these tests
need neither discovery libraries, Paramiko, AWS credentials, nor tag hardware.
Run with: python -m unittest discover -s tests -p test_whaletag_connections.py -v
"""

import __future__
import importlib.util
import io
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        # Fail closed if a future change accidentally bypasses our SSH doubles.
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
            # Defer the existing getLANips union annotation on Python 3.7-3.9.
            # These tests exercise connection lifetimes, not discovery typing.
            code = compile(path.read_bytes(), str(path), "exec",
                           flags=__future__.annotations.compiler_flag,
                           dont_inherit=True)
            exec(code, self.tag.__dict__)

        self.factory = self.tag.paramiko.SSHClient
        self.ssh = self.factory.return_value
        self.sftp = self.ssh.open_sftp.return_value
        self.events = mock.Mock()
        self.events.attach_mock(self.sftp.close, "sftp_close")
        self.events.attach_mock(self.ssh.close, "ssh_close")
        self.stdout = mock.Mock()
        self.stdout.readline.return_value = "wt-offline\n"
        self.stdout.readlines.return_value = []
        self.ssh.exec_command.return_value = (None, self.stdout, None)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.tag.LOCAL_DATA_PATH = folder.name
        output = redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def download(self):
        return self.tag.download_remote_file("wt-offline", "/data/sample.raw")

    def assert_download_closed(self):
        self.assertEqual(self.events.mock_calls, [
            mock.call.sftp_close(), mock.call.ssh_close(),
        ])

    def test_download_success_closes_in_order_and_preserves_paths(self):
        self.assertIsNone(self.download())
        self.sftp.get.assert_called_once_with(
            "/data/sample.raw",
            os.path.join(self.tag.LOCAL_DATA_PATH, "wt-offline", "sample.raw"),
        )
        self.assert_download_closed()

    def test_download_constructor_failure_preserves_error(self):
        error = RuntimeError("constructor failed")
        self.factory.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            self.download()
        self.assertIs(caught.exception, error)
        self.ssh.close.assert_not_called()
        self.sftp.close.assert_not_called()

    def test_download_setup_failures_close_only_acquired_ssh(self):
        for method in ("set_missing_host_key_policy", "connect", "open_sftp"):
            with self.subTest(method=method):
                error = OSError(method)
                operation = getattr(self.ssh, method)
                operation.side_effect = error
                with self.assertRaises(OSError) as caught:
                    self.download()
                self.assertIs(caught.exception, error)
                self.ssh.close.assert_called_once_with()
                self.sftp.close.assert_not_called()
                self.sftp.get.assert_not_called()
                operation.side_effect = None
                self.ssh.close.reset_mock()

    def test_download_transfer_failure_closes_both(self):
        error = OSError("transfer failed")
        self.sftp.get.side_effect = error
        with self.assertRaises(OSError) as caught:
            self.download()
        self.assertIs(caught.exception, error)
        self.assert_download_closed()

    def test_download_interruption_closes_both(self):
        for error in (KeyboardInterrupt(), SystemExit()):
            with self.subTest(error=type(error).__name__):
                self.sftp.get.side_effect = error
                with self.assertRaises(type(error)) as caught:
                    self.download()
                self.assertIs(caught.exception, error)
                self.assert_download_closed()
                self.events.reset_mock()

    def test_interruption_survives_close_failures(self):
        error = KeyboardInterrupt()
        self.sftp.get.side_effect = error
        self.sftp.close.side_effect = OSError("sftp close failed")
        self.ssh.close.side_effect = OSError("ssh close failed")
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.download()
        self.assertIs(caught.exception, error)
        self.assert_download_closed()

    def test_sftp_close_failure_still_closes_ssh(self):
        error = OSError("sftp close failed")
        self.sftp.close.side_effect = error
        with self.assertRaises(OSError) as caught:
            self.download()
        self.assertIs(caught.exception, error)
        self.assert_download_closed()

    def test_ssh_close_failure_on_success_is_reported(self):
        error = OSError("ssh close failed")
        self.ssh.close.side_effect = error
        with self.assertRaises(OSError) as caught:
            self.download()
        self.assertIs(caught.exception, error)
        self.assert_download_closed()

    def test_transfer_error_survives_both_close_failures(self):
        error = OSError("transfer failed")
        self.sftp.get.side_effect = error
        self.sftp.close.side_effect = RuntimeError("sftp close failed")
        self.ssh.close.side_effect = RuntimeError("ssh close failed")
        with self.assertRaises(OSError) as caught:
            self.download()
        self.assertIs(caught.exception, error)
        self.assert_download_closed()

    def test_first_close_error_survives_second_close_failure(self):
        error = OSError("sftp close failed")
        self.sftp.close.side_effect = error
        self.ssh.close.side_effect = RuntimeError("ssh close failed")
        with self.assertRaises(OSError) as caught:
            self.download()
        self.assertIs(caught.exception, error)
        self.assert_download_closed()

    def test_repeated_failed_downloads_close_each_client(self):
        clients = [mock.Mock() for _ in range(3)]
        self.factory.side_effect = clients
        for client in clients:
            client.open_sftp.side_effect = OSError("sftp setup failed")
            with self.assertRaises(OSError):
                self.download()
        for client in clients:
            client.close.assert_called_once_with()

    def test_probe_success_preserves_result_and_closes_once(self):
        for name, result in (("can_connect", True),
                             ("get_hostname_by_addr", "wt-offline")):
            with self.subTest(function=name):
                self.assertEqual(getattr(self.tag, name)("wt-offline"), result)
                self.ssh.connect.assert_called_once_with(
                    hostname="wt-offline", username=self.tag.DEFAULT_USERNAME,
                    password=self.tag.DEFAULT_PASSWORD,
                )
                if name == "get_hostname_by_addr":
                    self.ssh.exec_command.assert_called_once_with("hostname")
                else:
                    self.ssh.exec_command.assert_not_called()
                self.ssh.close.assert_called_once_with()
                self.ssh.reset_mock()

    def test_probe_failures_preserve_sentinel_and_close(self):
        for name, result in (("can_connect", False),
                             ("get_hostname_by_addr", "")):
            for error in (OSError("connect failed"), KeyboardInterrupt()):
                with self.subTest(function=name, error=type(error).__name__):
                    self.ssh.connect.side_effect = error
                    self.assertEqual(getattr(self.tag, name)("wt-offline"), result)
                    self.ssh.close.assert_called_once_with()
                    self.ssh.close.reset_mock()

    def test_probe_constructor_failure_preserves_sentinel(self):
        self.factory.side_effect = RuntimeError("constructor failed")
        self.assertFalse(self.tag.can_connect("wt-offline"))
        self.assertEqual(self.tag.get_hostname_by_addr("wt-offline"), "")
        self.ssh.close.assert_not_called()

    def test_probe_close_failure_preserves_sentinel(self):
        self.ssh.close.side_effect = OSError("close failed")
        self.assertFalse(self.tag.can_connect("wt-offline"))
        self.ssh.close.assert_called_once_with()
        self.ssh.close.reset_mock()
        self.assertEqual(self.tag.get_hostname_by_addr("wt-offline"), "")
        self.ssh.close.assert_called_once_with()

    def test_hostname_command_failure_closes_ssh(self):
        self.ssh.exec_command.side_effect = OSError("command failed")
        self.assertEqual(self.tag.get_hostname_by_addr("wt-offline"), "")
        self.ssh.close.assert_called_once_with()

    def test_file_listing_preserves_hash_filtering_and_closes(self):
        folder = Path(self.tag.LOCAL_DATA_PATH) / "wt-offline"
        folder.mkdir()
        (folder / "same.raw").touch()
        (folder / "changed.raw").touch()
        self.stdout.readlines.return_value = [
            "new.raw\n", "same.raw\n", "changed.raw\n",
        ]
        self.tag.sha256sum.side_effect = ["same-hash", "old-hash"]
        self.stdout.read.side_effect = [b"same-hash  same.raw",
                                        b"new-hash  changed.raw"]
        self.assertEqual(self.tag.create_filelist_to_download("wt-offline"), [
            os.path.join(os.path.normpath("/data"), "new.raw"),
            os.path.join(os.path.normpath("/data"), "changed.raw"),
        ])
        remote_folder = os.path.normpath("/data")
        self.assertEqual(self.ssh.exec_command.call_args_list, [
            mock.call("ls -p " + remote_folder + "| grep -v /"),
            mock.call("sha256sum " + os.path.join(remote_folder, "same.raw")),
            mock.call("sha256sum " + os.path.join(remote_folder, "changed.raw")),
        ])
        self.ssh.close.assert_called_once_with()

    def test_early_returns_do_not_create_or_close_another_client(self):
        self.tag.can_connect = mock.Mock(return_value=False)
        self.tag.stop_capture_service("wt-offline")
        self.tag.clean_tag("wt-offline")
        self.tag.can_connect.return_value = True
        self.tag.stop_capture_service = mock.Mock()
        self.tag.create_filelist_to_download = mock.Mock(return_value=["new.raw"])
        self.tag.clean_tag("wt-offline")
        self.factory.assert_not_called()
        self.ssh.close.assert_not_called()

    def single_client_operations(self):
        # Exercise only each function's owned client; prerequisites are inert.
        self.tag.can_connect = mock.Mock(return_value=True)
        stop = self.tag.stop_capture_service
        clean = self.tag.clean_tag
        listing = self.tag.create_filelist_to_download
        self.tag.stop_capture_service = mock.Mock()
        self.tag.create_filelist_to_download = mock.Mock(return_value=[])
        return listing, stop, clean

    def test_single_client_operations_close_on_success(self):
        commands = {
            "create_filelist_to_download": "ls -p " + os.path.normpath("/data") + "| grep -v /",
            "stop_capture_service": "sudo systemctl stop ceti-tag-data-capture",
            "clean_tag": "sudo rm -rf " + os.path.join("/data/", "*.*"),
        }
        for operation in self.single_client_operations():
            with self.subTest(function=operation.__name__):
                result = operation("wt-offline")
                self.assertEqual(result, [] if operation.__name__ ==
                                 "create_filelist_to_download" else None)
                self.ssh.exec_command.assert_called_once_with(commands[operation.__name__])
                self.ssh.close.assert_called_once_with()
                self.ssh.reset_mock()

    def test_single_client_constructor_failures_preserve_error(self):
        error = RuntimeError("constructor failed")
        self.factory.side_effect = error
        for operation in self.single_client_operations():
            with self.subTest(function=operation.__name__):
                with self.assertRaises(RuntimeError) as caught:
                    operation("wt-offline")
                self.assertIs(caught.exception, error)
        self.ssh.close.assert_not_called()

    def test_single_client_errors_close_and_preserve_original_error(self):
        operations = self.single_client_operations()
        for method in ("set_missing_host_key_policy", "connect", "exec_command"):
            for operation in operations:
                with self.subTest(function=operation.__name__, method=method):
                    error = OSError(method)
                    getattr(self.ssh, method).side_effect = error
                    self.ssh.close.side_effect = RuntimeError("close failed")
                    with self.assertRaises(OSError) as caught:
                        operation("wt-offline")
                    self.assertIs(caught.exception, error)
                    self.ssh.close.assert_called_once_with()
                    self.ssh.close.reset_mock()
                    getattr(self.ssh, method).side_effect = None


if __name__ == "__main__":
    unittest.main()
