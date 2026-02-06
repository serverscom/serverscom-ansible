# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import pytest
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerPower,
)  # noqa
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    APIError404,
    APIError409,
)


__metaclass__ = type


def create_power_instance(state="on", wait=60, checkmode=False):
    """Create a ScSbmServerPower instance with mocked API."""
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api:
        instance = ScSbmServerPower(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            state=state,
            wait=wait,
            checkmode=checkmode,
        )
        return instance, mock_api


def test_power_on_already_on():
    instance, _mock_api = create_power_instance(state="on")
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_on",
        "status": "active",
    }

    result = instance.power_on()

    assert result["changed"] is False
    assert result["power_status"] == "powered_on"
    instance.api.post_sbm_server_power_on.assert_not_called()


def test_power_off_already_off():
    instance, _mock_api = create_power_instance(state="off")
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_off",
        "status": "active",
    }

    result = instance.power_off()

    assert result["changed"] is False
    assert result["power_status"] == "powered_off"
    instance.api.post_sbm_server_power_off.assert_not_called()


def test_power_on_checkmode():
    instance, _mock_api = create_power_instance(state="on", checkmode=True)
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_off",
        "status": "active",
    }

    result = instance.power_on()

    assert result["changed"] is True
    instance.api.post_sbm_server_power_on.assert_not_called()


def test_power_off_checkmode():
    instance, _mock_api = create_power_instance(state="off", checkmode=True)
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_on",
        "status": "active",
    }

    result = instance.power_off()

    assert result["changed"] is True
    instance.api.post_sbm_server_power_off.assert_not_called()


def test_power_cycle_checkmode():
    instance, _mock_api = create_power_instance(state="cycle", checkmode=True)
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_on",
        "status": "active",
    }

    result = instance.power_cycle()

    assert result["changed"] is True
    instance.api.post_sbm_server_power_cycle.assert_not_called()


def test_run_state_on():
    instance, _mock_api = create_power_instance(state="on")
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_on",
        "status": "active",
    }

    result = instance.run()

    assert result["changed"] is False


def test_run_state_off():
    instance, _mock_api = create_power_instance(state="off")
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_off",
        "status": "active",
    }

    result = instance.run()

    assert result["changed"] is False


def test_run_state_cycle_checkmode():
    instance, _mock_api = create_power_instance(state="cycle", checkmode=True)
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_on",
        "status": "active",
    }

    result = instance.run()

    assert result["changed"] is True


def test_run_unknown_state():
    instance, _mock_api = create_power_instance(state="invalid")

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "Unknown state" in str(exc_info.value.msg)


def test_power_on_server_not_found():
    instance, _mock_api = create_power_instance(state="on")
    instance.api.get_sbm_servers.side_effect = APIError404(
        msg="Not found", api_url="/test", status_code=404
    )

    with pytest.raises(ModuleError) as exc_info:
        instance.power_on()

    assert "not found" in str(exc_info.value.msg)


def test_power_off_server_not_found():
    instance, _mock_api = create_power_instance(state="off")
    instance.api.get_sbm_servers.side_effect = APIError404(
        msg="Not found", api_url="/test", status_code=404
    )

    with pytest.raises(ModuleError) as exc_info:
        instance.power_off()

    assert "not found" in str(exc_info.value.msg)


def test_power_cycle_server_not_found():
    instance, _mock_api = create_power_instance(state="cycle")
    instance.api.get_sbm_servers.side_effect = APIError404(
        msg="Not found", api_url="/test", status_code=404
    )

    with pytest.raises(ModuleError) as exc_info:
        instance.power_cycle()

    assert "not found" in str(exc_info.value.msg)


CONFLICT_MSG = (
    '409 Conflict. b\'{"message":"Power management unavailable","code":"CONFLICT"}\''
)


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_power_off_409_conflict_retry_success(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_power_instance(state="off", wait=60)
    instance.api.get_sbm_servers.side_effect = [
        {"id": "test-server", "power_status": "powered_on", "status": "active"},
        {"id": "test-server", "power_status": "powered_off", "status": "active"},
    ]
    instance.api.post_sbm_server_power_off.side_effect = [
        APIError409(msg=CONFLICT_MSG, api_url="/test", status_code=409),
        None,
    ]

    result = instance.run()

    assert result["changed"] is True
    assert result["power_status"] == "powered_off"
    assert instance.api.post_sbm_server_power_off.call_count == 2


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_power_on_409_conflict_retry_success(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_power_instance(state="on", wait=60)
    instance.api.get_sbm_servers.side_effect = [
        {"id": "test-server", "power_status": "powered_off", "status": "active"},
        {"id": "test-server", "power_status": "powered_on", "status": "active"},
    ]
    instance.api.post_sbm_server_power_on.side_effect = [
        APIError409(msg=CONFLICT_MSG, api_url="/test", status_code=409),
        None,
    ]

    result = instance.run()

    assert result["changed"] is True
    assert instance.api.post_sbm_server_power_on.call_count == 2


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_power_409_conflict_timeout(mock_time):
    mock_time.time.side_effect = [0, 100000]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_power_instance(state="off", wait=60)
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_on",
        "status": "active",
    }
    instance.api.post_sbm_server_power_off.side_effect = APIError409(
        msg=CONFLICT_MSG, api_url="/test", status_code=409
    )

    with pytest.raises(APIError409):
        instance.run()


def test_power_409_non_conflict_not_retried():
    """409 with a code other than CONFLICT should not be retried."""
    non_conflict_msg = (
        '409 Conflict. b\'{"message":"Network is not ready",'
        '"code":"NETWORK_IS_NOT_READY"}\''
    )
    instance, _mock_api = create_power_instance(state="off", wait=60)
    instance.api.get_sbm_servers.return_value = {
        "id": "test-server",
        "power_status": "powered_on",
        "status": "active",
    }
    instance.api.post_sbm_server_power_off.side_effect = APIError409(
        msg=non_conflict_msg, api_url="/test", status_code=409
    )

    with pytest.raises(APIError409):
        instance.run()

    instance.api.post_sbm_server_power_off.assert_called_once()
