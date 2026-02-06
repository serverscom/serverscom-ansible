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
    ScSbmServerCreate,
    ScSbmServerDelete,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    APIError404,
    APIError409,
)


__metaclass__ = type

READY_SERVER = {
    "id": "srv123",
    "title": "test-host",
    "type": "sbm_server",
    "status": "active",
    "operational_status": "normal",
    "power_status": "powered_on",
    "location_id": 1,
    "location_code": "AMS7",
}

PENDING_SERVER = {
    "id": "srv123",
    "title": "test-host",
    "type": "sbm_server",
    "status": "init",
    "operational_status": "provisioning",
    "power_status": "unknown",
    "location_id": 1,
    "location_code": "AMS7",
}


def create_create_instance(
    wait=86400,
    update_interval=60,
    checkmode=False,
    ssh_key_fingerprints=None,
    user_data=None,
):
    """Create a ScSbmServerCreate instance with mocked API."""
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ):
        instance = ScSbmServerCreate(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            location_id=1,
            sbm_flavor_model_id=42,
            hostname="test-host",
            operating_system_id=100,
            ssh_key_fingerprints=ssh_key_fingerprints,
            user_data=user_data,
            wait=wait,
            update_interval=update_interval,
            checkmode=checkmode,
        )
        return instance


def create_delete_instance(
    wait=600,
    update_interval=30,
    retry_on_conflicts=True,
    wait_for_deletion=False,
    checkmode=False,
):
    """Create a ScSbmServerDelete instance with mocked API."""
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ):
        instance = ScSbmServerDelete(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="srv123",
            wait=wait,
            update_interval=update_interval,
            retry_on_conflicts=retry_on_conflicts,
            wait_for_deletion=wait_for_deletion,
            checkmode=checkmode,
        )
        return instance


# ─── ScSbmServerCreate tests ───


def test_create_checkmode():
    instance = create_create_instance(checkmode=True)

    result = instance.run()

    assert result["changed"] is True
    assert "check_mode" in result["info"]
    instance.api.post_sbm_servers.assert_not_called()


def test_create_no_wait():
    instance = create_create_instance(wait=0)
    instance.api.post_sbm_servers.return_value = [PENDING_SERVER.copy()]

    result = instance.run()

    assert result["changed"] is True
    assert result["id"] == "srv123"
    instance.api.post_sbm_servers.assert_called_once()
    instance.api.get_sbm_servers.assert_not_called()


def test_create_immediate_ready():
    instance = create_create_instance(wait=86400)
    instance.api.post_sbm_servers.return_value = [READY_SERVER.copy()]

    result = instance.run()

    assert result["changed"] is True
    assert result["id"] == "srv123"
    instance.api.get_sbm_servers.assert_not_called()


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_create_polls_until_ready(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance = create_create_instance(wait=86400, update_interval=60)
    instance.api.post_sbm_servers.return_value = [PENDING_SERVER.copy()]
    instance.api.get_sbm_servers.side_effect = [
        PENDING_SERVER.copy(),
        READY_SERVER.copy(),
    ]

    result = instance.run()

    assert result["changed"] is True
    assert result["status"] == "active"
    assert instance.api.get_sbm_servers.call_count == 2


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_create_timeout(mock_time):
    mock_time.time.side_effect = [0, 0, 100000]
    mock_time.sleep = mock.MagicMock()

    instance = create_create_instance(wait=100, update_interval=10)
    instance.api.post_sbm_servers.return_value = [PENDING_SERVER.copy()]
    instance.api.get_sbm_servers.return_value = PENDING_SERVER.copy()

    with pytest.raises(WaitError) as exc_info:
        instance.run()

    assert "Timeout" in exc_info.value.msg


def test_create_interval_greater_than_wait():
    with pytest.raises(ModuleError) as exc_info:
        create_create_instance(wait=30, update_interval=60)

    assert "Update interval" in exc_info.value.msg


def test_create_ssh_keys_passthrough():
    instance = create_create_instance(
        wait=0,
        ssh_key_fingerprints=["aa:bb:cc"],
        user_data="#cloud-config",
    )
    instance.api.post_sbm_servers.return_value = [PENDING_SERVER.copy()]

    instance.run()

    call_kwargs = instance.api.post_sbm_servers.call_args
    assert call_kwargs[1]["ssh_key_fingerprints"] == ["aa:bb:cc"]
    assert call_kwargs[1]["user_data"] == "#cloud-config"


def test_create_hosts_array():
    instance = create_create_instance(wait=0)
    instance.api.post_sbm_servers.return_value = [PENDING_SERVER.copy()]

    instance.run()

    call_kwargs = instance.api.post_sbm_servers.call_args
    assert call_kwargs[1]["hosts"] == [{"hostname": "test-host"}]


def test_create_takes_first_result():
    instance = create_create_instance(wait=0)
    server1 = PENDING_SERVER.copy()
    server2 = PENDING_SERVER.copy()
    server2["id"] = "srv456"
    instance.api.post_sbm_servers.return_value = [server1, server2]

    result = instance.run()

    assert result["id"] == "srv123"


# ─── ScSbmServerDelete tests ───


def test_delete_found():
    instance = create_delete_instance()
    instance.api.get_sbm_servers.side_effect = [
        READY_SERVER.copy(),
        APIError404(msg="Not found", api_url="/test", status_code=404),
    ]

    result = instance.run()

    assert result["changed"] is True
    instance.api.delete_sbm_server.assert_called_once_with("srv123")


def test_delete_not_found():
    instance = create_delete_instance()
    instance.api.get_sbm_servers.side_effect = APIError404(
        msg="Not found", api_url="/test", status_code=404
    )

    result = instance.run()

    assert result["changed"] is False
    instance.api.delete_sbm_server.assert_not_called()


def test_delete_checkmode():
    instance = create_delete_instance(checkmode=True)
    instance.api.get_sbm_servers.return_value = READY_SERVER.copy()

    result = instance.run()

    assert result["changed"] is True
    instance.api.delete_sbm_server.assert_not_called()


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_delete_409_retry_success(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance = create_delete_instance(retry_on_conflicts=True)
    instance.api.get_sbm_servers.side_effect = [
        READY_SERVER.copy(),
        APIError404(msg="Not found", api_url="/test", status_code=404),
    ]
    instance.api.delete_sbm_server.side_effect = [
        APIError409(msg="Conflict", api_url="/test", status_code=409),
        None,
    ]

    result = instance.run()

    assert result["changed"] is True
    assert instance.api.delete_sbm_server.call_count == 2


def test_delete_409_no_retry():
    instance = create_delete_instance(retry_on_conflicts=False)
    instance.api.get_sbm_servers.return_value = READY_SERVER.copy()
    instance.api.delete_sbm_server.side_effect = APIError409(
        msg="Conflict", api_url="/test", status_code=409
    )

    with pytest.raises(APIError409):
        instance.run()


def test_delete_404_during_delete():
    instance = create_delete_instance()
    instance.api.get_sbm_servers.side_effect = [
        READY_SERVER.copy(),
        APIError404(msg="Not found", api_url="/test", status_code=404),
    ]
    instance.api.delete_sbm_server.side_effect = APIError404(
        msg="Not found", api_url="/test", status_code=404
    )

    result = instance.run()

    assert result["changed"] is True


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_delete_wait_timeout(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 100000]
    mock_time.sleep = mock.MagicMock()

    instance = create_delete_instance(
        wait=100, update_interval=10, wait_for_deletion=True
    )
    instance.api.get_sbm_servers.return_value = READY_SERVER.copy()
    instance.api.delete_sbm_server.return_value = None

    with pytest.raises(WaitError) as exc_info:
        instance.run()

    assert "Timeout" in exc_info.value.msg


def test_delete_interval_greater_than_wait():
    with pytest.raises(ModuleError) as exc_info:
        create_delete_instance(wait=10, update_interval=60)

    assert "Update interval" in exc_info.value.msg
