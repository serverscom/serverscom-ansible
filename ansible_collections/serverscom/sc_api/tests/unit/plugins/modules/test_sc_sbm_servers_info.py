# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServersInfo,
)  # noqa


__metaclass__ = type


SERVER_1 = {
    "id": "srv-1",
    "title": "web-01",
    "status": "active",
    "location_id": 1,
    "labels": {"env": "prod"},
}

SERVER_2 = {
    "id": "srv-2",
    "title": "db-01",
    "status": "active",
    "location_id": 2,
    "labels": {},
}

SERVERS = [SERVER_1, SERVER_2]


def test_run_returns_servers():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_servers.return_value = iter(SERVERS)

        info = ScSbmServersInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
        )
        result = info.run()

        assert result["changed"] is False
        assert result["sbm_servers"] == SERVERS


def test_run_with_search_pattern():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_servers.return_value = iter([SERVER_1])

        info = ScSbmServersInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            search_pattern="web",
        )
        result = info.run()

        assert result["changed"] is False
        assert len(result["sbm_servers"]) == 1
        mock_instance.list_sbm_servers.assert_called_once_with(
            search_pattern="web",
            location_id=None,
            rack_id=None,
            label_selector=None,
        )


def test_run_with_location_filter():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_servers.return_value = iter([SERVER_1])

        info = ScSbmServersInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            location_id=1,
        )
        result = info.run()

        assert result["changed"] is False
        mock_instance.list_sbm_servers.assert_called_once_with(
            search_pattern=None,
            location_id=1,
            rack_id=None,
            label_selector=None,
        )


def test_run_with_label_selector():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_servers.return_value = iter([SERVER_1])

        info = ScSbmServersInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            label_selector="env=prod",
        )
        result = info.run()

        assert result["changed"] is False
        mock_instance.list_sbm_servers.assert_called_once_with(
            search_pattern=None,
            location_id=None,
            rack_id=None,
            label_selector="env=prod",
        )


def test_run_empty_result():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_servers.return_value = iter([])

        info = ScSbmServersInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
        )
        result = info.run()

        assert result["changed"] is False
        assert result["sbm_servers"] == []
