import ipaddress
import sys
from unittest import mock

import pytest

from ceti.whaletag import find_ssh_servers


class TestFindSshServers:
    """Tests for find_ssh_servers() -- issue #40."""

    @mock.patch("ceti.whaletag.findssh.get_hosts", new_callable=mock.Mock)
    @mock.patch("ceti.whaletag.findssh.netfromaddress")
    @mock.patch("ceti.whaletag.getLANips")
    @mock.patch("ceti.whaletag.asyncio.run")
    def test_restores_stdout_on_success(
        self, mock_asyncio_run, mock_get_lanips, mock_netfromaddress, mock_get_hosts
    ):
        mock_get_lanips.return_value = [ipaddress.ip_address("192.168.1.1")]
        mock_netfromaddress.return_value = "fake-netspec"
        mock_get_hosts.return_value = "fake-coro"
        mock_asyncio_run.side_effect = [
            [("192.168.1.10", 22)],
            [("192.168.11.2", 22)],
        ]

        orig_stdout = sys.stdout
        result = find_ssh_servers()

        assert sys.stdout is orig_stdout
        assert result == ["192.168.1.10", "192.168.11.2"]

    @mock.patch("ceti.whaletag.findssh.get_hosts", new_callable=mock.Mock)
    @mock.patch("ceti.whaletag.findssh.netfromaddress")
    @mock.patch("ceti.whaletag.getLANips")
    @mock.patch("ceti.whaletag.asyncio.run")
    def test_restores_stdout_on_first_run_error(
        self, mock_asyncio_run, mock_get_lanips, mock_netfromaddress, mock_get_hosts
    ):
        mock_get_lanips.return_value = [ipaddress.ip_address("192.168.1.1")]
        mock_netfromaddress.return_value = "fake-netspec"
        mock_get_hosts.return_value = "fake-coro"
        mock_asyncio_run.side_effect = RuntimeError("first run failed")

        orig_stdout = sys.stdout
        with pytest.raises(RuntimeError, match="first run failed"):
            find_ssh_servers()
        assert sys.stdout is orig_stdout

    @mock.patch("ceti.whaletag.findssh.get_hosts", new_callable=mock.Mock)
    @mock.patch("ceti.whaletag.findssh.netfromaddress")
    @mock.patch("ceti.whaletag.getLANips")
    @mock.patch("ceti.whaletag.asyncio.run")
    def test_restores_stdout_on_second_run_error(
        self, mock_asyncio_run, mock_get_lanips, mock_netfromaddress, mock_get_hosts
    ):
        mock_get_lanips.return_value = [ipaddress.ip_address("192.168.1.1")]
        mock_netfromaddress.return_value = "fake-netspec"
        mock_get_hosts.return_value = "fake-coro"
        mock_asyncio_run.side_effect = [
            [("192.168.1.10", 22)],
            RuntimeError("second run failed"),
        ]

        orig_stdout = sys.stdout
        with pytest.raises(RuntimeError, match="second run failed"):
            find_ssh_servers()
        assert sys.stdout is orig_stdout
