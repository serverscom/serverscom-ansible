# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import pytest
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerNetwork,
)  # noqa
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    APIError404,
    APIError409,
)


__metaclass__ = type


NETWORK = {
    "id": "net-1",
    "title": "Private",
    "status": "new",
    "cidr": None,
    "family": "ipv4",
    "interface_type": "private",
    "distribution_method": "gateway",
    "additional": True,
}

ACTIVE_NETWORK = {
    "id": "net-1",
    "title": "Private",
    "status": "active",
    "cidr": "10.128.1.0/29",
    "family": "ipv4",
    "interface_type": "private",
    "distribution_method": "gateway",
    "additional": True,
}

DELETED_NETWORK = {
    "id": "net-1",
    "title": "Private",
    "status": "removed",
    "cidr": "10.128.1.0/29",
    "family": "ipv4",
    "interface_type": "private",
    "distribution_method": "gateway",
    "additional": True,
}


def create_network_instance(
    state="present",
    network_id=None,
    mask=29,
    wait=600,
    update_interval=10,
    checkmode=False,
):
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ):
        return ScSbmServerNetwork(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            state=state,
            network_id=network_id,
            mask=mask,
            distribution_method="gateway",
            wait=wait,
            update_interval=update_interval,
            checkmode=checkmode,
        )


def test_create_no_wait():
    instance = create_network_instance(state="present", mask=29, wait=0)
    instance.api.post_sbm_server_private_ipv4_network.return_value = dict(NETWORK)

    result = instance.run()

    assert result["changed"] is True
    assert result["status"] == "new"
    assert result["cidr"] is None
    instance.api.post_sbm_server_private_ipv4_network.assert_called_once_with(
        server_id="test-server",
        mask=29,
        distribution_method="gateway",
    )
    instance.api.get_sbm_server_network.assert_not_called()


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_create_immediate_active(mock_time):
    instance = create_network_instance(state="present", mask=29)
    instance.api.post_sbm_server_private_ipv4_network.return_value = dict(
        ACTIVE_NETWORK
    )

    result = instance.run()

    assert result["changed"] is True
    assert result["status"] == "active"
    assert result["cidr"] == "10.128.1.0/29"
    instance.api.get_sbm_server_network.assert_not_called()


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_create_polls_until_active(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance = create_network_instance(state="present", mask=29)
    instance.api.post_sbm_server_private_ipv4_network.return_value = dict(NETWORK)
    instance.api.get_sbm_server_network.side_effect = [
        dict(NETWORK),
        dict(ACTIVE_NETWORK),
    ]

    result = instance.run()

    assert result["changed"] is True
    assert result["status"] == "active"
    assert result["cidr"] == "10.128.1.0/29"
    assert instance.api.get_sbm_server_network.call_count == 2


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_create_timeout(mock_time):
    mock_time.time.side_effect = [0, 0, 100000]
    mock_time.sleep = mock.MagicMock()

    instance = create_network_instance(
        state="present", mask=29, wait=100, update_interval=10
    )
    instance.api.post_sbm_server_private_ipv4_network.return_value = dict(NETWORK)
    instance.api.get_sbm_server_network.return_value = dict(NETWORK)

    with pytest.raises(WaitError) as exc_info:
        instance.run()

    assert "Timeout" in exc_info.value.msg


def test_create_interval_greater_than_wait():
    with pytest.raises(ModuleError) as exc_info:
        create_network_instance(wait=5, update_interval=10)

    assert "Update interval" in exc_info.value.msg


def test_create_network_checkmode():
    instance = create_network_instance(state="present", mask=29, checkmode=True)

    result = instance.run()

    assert result["changed"] is True
    instance.api.post_sbm_server_private_ipv4_network.assert_not_called()


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_delete_waits_for_removal(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance = create_network_instance(state="absent", network_id="net-1", mask=None)
    instance.api.get_sbm_server_network.side_effect = [
        dict(ACTIVE_NETWORK),  # initial check
        dict(ACTIVE_NETWORK),  # first poll (still active)
        APIError404(msg="Not found", api_url="/test", status_code=404),  # gone
    ]
    instance.api.delete_sbm_server_network.return_value = None

    result = instance.run()

    assert result["changed"] is True
    instance.api.delete_sbm_server_network.assert_called_once_with(
        "test-server", "net-1"
    )


def test_delete_no_wait():
    instance = create_network_instance(
        state="absent", network_id="net-1", mask=None, wait=0
    )
    instance.api.get_sbm_server_network.return_value = dict(ACTIVE_NETWORK)
    instance.api.delete_sbm_server_network.return_value = None

    result = instance.run()

    assert result["changed"] is True
    instance.api.delete_sbm_server_network.assert_called_once()
    # get called once for initial check only, no polling
    assert instance.api.get_sbm_server_network.call_count == 1


def test_delete_network_not_found():
    instance = create_network_instance(state="absent", network_id="net-1", mask=None)
    instance.api.get_sbm_server_network.side_effect = APIError404(
        msg="Not found", api_url="/test", status_code=404
    )

    result = instance.run()

    assert result["changed"] is False
    instance.api.delete_sbm_server_network.assert_not_called()


def test_delete_already_removed():
    instance = create_network_instance(state="absent", network_id="net-1", mask=None)
    instance.api.get_sbm_server_network.return_value = dict(DELETED_NETWORK)

    result = instance.run()

    assert result["changed"] is False
    instance.api.delete_sbm_server_network.assert_not_called()


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_delete_409_still_succeeds(mock_time):
    mock_time.time.side_effect = [0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance = create_network_instance(state="absent", network_id="net-1", mask=None)
    instance.api.get_sbm_server_network.side_effect = [
        dict(ACTIVE_NETWORK),  # initial check
        dict(DELETED_NETWORK),  # poll returns removed
    ]
    instance.api.delete_sbm_server_network.side_effect = APIError409(
        msg="Conflict", api_url="/test", status_code=409
    )

    result = instance.run()

    assert result["changed"] is True


def test_delete_network_checkmode():
    instance = create_network_instance(
        state="absent", network_id="net-1", mask=None, checkmode=True
    )
    instance.api.get_sbm_server_network.return_value = dict(ACTIVE_NETWORK)

    result = instance.run()

    assert result["changed"] is True
    instance.api.delete_sbm_server_network.assert_not_called()


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_delete_wait_timeout(mock_time):
    # _wait_for_network_gone: time(start), GET, sleep, time(elapsed) -> timeout
    mock_time.time.side_effect = [0, 100000]
    mock_time.sleep = mock.MagicMock()

    instance = create_network_instance(
        state="absent", network_id="net-1", mask=None, wait=100, update_interval=10
    )
    instance.api.get_sbm_server_network.side_effect = [
        dict(ACTIVE_NETWORK),  # initial check in delete()
        dict(ACTIVE_NETWORK),  # first poll in _wait_for_network_gone
    ]
    instance.api.delete_sbm_server_network.return_value = None

    with pytest.raises(WaitError) as exc_info:
        instance.run()

    assert "Timeout" in exc_info.value.msg


def test_unknown_state():
    instance = create_network_instance(state="present")
    instance.state = "invalid"

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "Unknown state" in str(exc_info.value.msg)
