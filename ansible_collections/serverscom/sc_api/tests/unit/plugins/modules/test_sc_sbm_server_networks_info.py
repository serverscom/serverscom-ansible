# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerNetworksInfo,
)  # noqa


__metaclass__ = type


NETWORK_1 = {
    "id": "net-1",
    "title": "Public",
    "status": "active",
    "cidr": "100.0.8.0/29",
    "family": "ipv4",
    "interface_type": "public",
    "distribution_method": "gateway",
    "additional": False,
}

NETWORK_2 = {
    "id": "net-2",
    "title": "Private",
    "status": "active",
    "cidr": "10.128.1.0/29",
    "family": "ipv4",
    "interface_type": "private",
    "distribution_method": "gateway",
    "additional": False,
}

NETWORKS = [NETWORK_1, NETWORK_2]


def test_list_networks():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_server_networks.return_value = iter(NETWORKS)

        info = ScSbmServerNetworksInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
        )
        result = info.run()

        assert result["changed"] is False
        assert result["networks"] == NETWORKS


def test_list_networks_with_filter():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_server_networks.return_value = iter([NETWORK_2])

        info = ScSbmServerNetworksInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            family="ipv4",
            interface_type="private",
        )
        result = info.run()

        assert result["changed"] is False
        assert len(result["networks"]) == 1
        mock_instance.list_sbm_server_networks.assert_called_once_with(
            server_id="test-server",
            search_pattern=None,
            family="ipv4",
            interface_type="private",
            distribution_method=None,
            additional=None,
        )


def test_get_single_network():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.get_sbm_server_network.return_value = dict(NETWORK_1)

        info = ScSbmServerNetworksInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            network_id="net-1",
        )
        result = info.run()

        assert result["changed"] is False
        assert result["id"] == "net-1"
        mock_instance.get_sbm_server_network.assert_called_once_with(
            "test-server", "net-1"
        )


def test_list_networks_empty():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_server_networks.return_value = iter([])

        info = ScSbmServerNetworksInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
        )
        result = info.run()

        assert result["changed"] is False
        assert result["networks"] == []
