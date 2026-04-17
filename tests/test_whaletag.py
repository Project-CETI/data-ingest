import logging
from unittest import mock

import paramiko
import pytest

from ceti.whaletag import can_connect, get_hostname_by_addr


class TestCanConnect:
    """Tests for can_connect() -- issue #39."""

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_successful_connection(self, mock_ssh_cls):
        assert can_connect("192.168.1.10") is True
        mock_ssh_cls.return_value.connect.assert_called_once()
        mock_ssh_cls.return_value.close.assert_called_once()

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_auth_failure_returns_false(self, mock_ssh_cls, caplog):
        mock_ssh_cls.return_value.connect.side_effect = (
            paramiko.AuthenticationException("Bad password")
        )
        with caplog.at_level(logging.ERROR):
            result = can_connect("192.168.1.10")

        assert result is False
        assert "Authentication failed" in caplog.text
        assert "192.168.1.10" in caplog.text

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_ssh_error_returns_false(self, mock_ssh_cls, caplog):
        mock_ssh_cls.return_value.connect.side_effect = (
            paramiko.SSHException("Protocol error")
        )
        with caplog.at_level(logging.ERROR):
            result = can_connect("192.168.1.10")

        assert result is False
        assert "SSH error" in caplog.text

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_network_error_returns_false(self, mock_ssh_cls, caplog):
        mock_ssh_cls.return_value.connect.side_effect = (
            OSError("Connection refused")
        )
        with caplog.at_level(logging.ERROR):
            result = can_connect("192.168.1.10")

        assert result is False
        assert "Network error" in caplog.text

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_keyboard_interrupt_not_caught(self, mock_ssh_cls):
        mock_ssh_cls.return_value.connect.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            can_connect("192.168.1.10")


class TestGetHostnameByAddr:
    """Tests for get_hostname_by_addr() -- issue #39."""

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_returns_hostname(self, mock_ssh_cls):
        mock_stdout = mock.Mock()
        mock_stdout.readline.return_value = "wt-b827eb123456\n"
        mock_ssh_cls.return_value.exec_command.return_value = (
            None, mock_stdout, None
        )

        result = get_hostname_by_addr("192.168.1.10")
        assert result == "wt-b827eb123456"

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_connection_failure_returns_empty(self, mock_ssh_cls, caplog):
        mock_ssh_cls.return_value.connect.side_effect = (
            paramiko.SSHException("Connection refused")
        )
        with caplog.at_level(logging.WARNING):
            result = get_hostname_by_addr("192.168.1.10")

        assert result == ""
        assert "Failed to get hostname" in caplog.text
        assert "192.168.1.10" in caplog.text

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_timeout_returns_empty(self, mock_ssh_cls, caplog):
        mock_ssh_cls.return_value.connect.side_effect = (
            OSError("Connection timed out")
        )
        with caplog.at_level(logging.WARNING):
            result = get_hostname_by_addr("192.168.1.10")

        assert result == ""
        assert "Connection timed out" in caplog.text

    @mock.patch("ceti.whaletag.paramiko.SSHClient")
    def test_keyboard_interrupt_not_caught(self, mock_ssh_cls):
        mock_ssh_cls.return_value.connect.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            get_hostname_by_addr("192.168.1.10")
