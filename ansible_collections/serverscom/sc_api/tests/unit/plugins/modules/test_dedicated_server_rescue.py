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
from ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server import (
    ScDedicatedServerRescue,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    APIError409,
    APIError412,
)


__metaclass__ = type


READY_SERVER = {
    "id": "test-server",
    "status": "active",
    "operational_status": "normal",
    "power_status": "powered_on",
}

RESCUE_SERVER = {
    "id": "test-server",
    "status": "active",
    "operational_status": "rescue_mode",
    "power_status": "powered_on",
}


def create_rescue_instance(
    state="rescue",
    auth_methods=None,
    ssh_key_fingerprints=None,
    ssh_key_name=None,
    wait=600,
    update_interval=10,
    checkmode=False,
):
    """Create a ScDedicatedServerRescue instance with mocked API."""
    if auth_methods is None and state == "rescue":
        auth_methods = ["password"]
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils"
        ".dedicated_server.ScApi"
    ) as mock_api:
        instance = ScDedicatedServerRescue(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            state=state,
            auth_methods=auth_methods,
            ssh_key_fingerprints=ssh_key_fingerprints,
            ssh_key_name=ssh_key_name,
            wait=wait,
            update_interval=update_interval,
            checkmode=checkmode,
        )
        return instance, mock_api


# --- Idempotency: steady states ---


def test_activate_already_activated():
    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "activated"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is False
    instance.api.post_dedicated_server_rescue_activate.assert_not_called()


def test_deactivate_already_deactivated():
    instance, _mock_api = create_rescue_instance(state="normal", auth_methods=None)
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "deactivated"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(READY_SERVER)

    result = instance.run()

    assert result["changed"] is False
    instance.api.post_dedicated_server_rescue_deactivate.assert_not_called()


# --- Idempotency: transitional states (wait for completion) ---


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_activate_while_activating(mock_time):
    mock_time.time.side_effect = [0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "activation"}],
        [{"name": "host_rescue_mode", "status": "activated"}],
    ]
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is False
    instance.api.post_dedicated_server_rescue_activate.assert_not_called()


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_deactivate_while_deactivating(mock_time):
    mock_time.time.side_effect = [0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="normal", auth_methods=None)
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "deactivation"}],
        [{"name": "host_rescue_mode", "status": "deactivated"}],
    ]
    instance.api.get_dedicated_servers.return_value = dict(READY_SERVER)

    result = instance.run()

    assert result["changed"] is False
    instance.api.post_dedicated_server_rescue_deactivate.assert_not_called()


# --- Check mode ---


def test_activate_checkmode():
    instance, _mock_api = create_rescue_instance(state="rescue", checkmode=True)
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "deactivated"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(READY_SERVER)

    result = instance.run()

    assert result["changed"] is True
    instance.api.post_dedicated_server_rescue_activate.assert_not_called()


def test_deactivate_checkmode():
    instance, _mock_api = create_rescue_instance(
        state="normal", auth_methods=None, checkmode=True
    )
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "activated"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is True
    instance.api.post_dedicated_server_rescue_deactivate.assert_not_called()


# --- Success flows ---


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_activate_success(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "deactivated"}],
        [{"name": "host_rescue_mode", "status": "activated"}],
    ]
    instance.api.post_dedicated_server_rescue_activate.return_value = {
        "name": "host_rescue_mode",
        "status": "activation",
    }
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is True
    assert result["operational_status"] == "rescue_mode"
    instance.api.post_dedicated_server_rescue_activate.assert_called_once_with(
        "test-server",
        auth_methods=["password"],
        ssh_key_fingerprints=None,
    )


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_deactivate_success(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="normal", auth_methods=None)
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "activated"}],
        [{"name": "host_rescue_mode", "status": "deactivated"}],
    ]
    instance.api.post_dedicated_server_rescue_deactivate.return_value = {
        "name": "host_rescue_mode",
        "status": "deactivation",
    }
    instance.api.get_dedicated_servers.return_value = dict(READY_SERVER)

    result = instance.run()

    assert result["changed"] is True
    assert result["operational_status"] == "normal"
    instance.api.post_dedicated_server_rescue_deactivate.assert_called_once_with(
        "test-server"
    )


# --- No wait (fire-and-forget) ---


def test_activate_no_wait():
    instance, _mock_api = create_rescue_instance(state="rescue", wait=0)
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "deactivated"},
    ]
    instance.api.post_dedicated_server_rescue_activate.return_value = {
        "name": "host_rescue_mode",
        "status": "activation",
    }
    instance.api.get_dedicated_servers.return_value = dict(READY_SERVER)

    result = instance.run()

    assert result["changed"] is True
    instance.api.post_dedicated_server_rescue_activate.assert_called_once()


def test_deactivate_no_wait():
    instance, _mock_api = create_rescue_instance(
        state="normal", auth_methods=None, wait=0
    )
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "activated"},
    ]
    instance.api.post_dedicated_server_rescue_deactivate.return_value = {
        "name": "host_rescue_mode",
        "status": "deactivation",
    }
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is True
    instance.api.post_dedicated_server_rescue_deactivate.assert_called_once()


# --- run() dispatcher ---


def test_run_state_rescue():
    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "activated"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is False


def test_run_state_normal():
    instance, _mock_api = create_rescue_instance(state="normal", auth_methods=None)
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "deactivated"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(READY_SERVER)

    result = instance.run()

    assert result["changed"] is False


def test_run_unknown_state():
    instance, _mock_api = create_rescue_instance(state="invalid", auth_methods=None)

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "Unknown state" in str(exc_info.value.msg)


# --- Error cases: feature status ---


def test_activate_unavailable():
    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "unavailable"},
    ]

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "unavailable" in str(exc_info.value.msg)


def test_activate_incompatible():
    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "incompatible"},
    ]

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "incompatible" in str(exc_info.value.msg)


def test_deactivate_unavailable():
    instance, _mock_api = create_rescue_instance(state="normal", auth_methods=None)
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "unavailable"},
    ]

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "unavailable" in str(exc_info.value.msg)


def test_feature_not_found():
    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "some_other_feature", "status": "activated"},
    ]

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "host_rescue_mode feature not found" in str(exc_info.value.msg)


# --- 409/412 retry ---


INCOMPATIBLE_STATE_MSG = (
    '409 Conflict. b\'{"message":"Incompatible feature state",'
    '"code":"INCOMPATIBLE_FEATURE_STATE"}\''
)

PRECONDITION_FAILED_MSG = (
    '412 Precondition Failed. b\'{"message":"Host is not ready",'
    '"code":"PRECONDITION_FAILED"}\''
)


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_409_retry_success(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "deactivated"}],
        [{"name": "host_rescue_mode", "status": "activated"}],
    ]
    instance.api.post_dedicated_server_rescue_activate.side_effect = [
        APIError409(
            msg=INCOMPATIBLE_STATE_MSG, api_url="/test", status_code=409
        ),
        {"name": "host_rescue_mode", "status": "activation"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is True
    assert instance.api.post_dedicated_server_rescue_activate.call_count == 2


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_412_retry_success(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "deactivated"}],
        [{"name": "host_rescue_mode", "status": "activated"}],
    ]
    instance.api.post_dedicated_server_rescue_activate.side_effect = [
        APIError412(
            msg=PRECONDITION_FAILED_MSG, api_url="/test", status_code=412
        ),
        {"name": "host_rescue_mode", "status": "activation"},
    ]
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is True
    assert instance.api.post_dedicated_server_rescue_activate.call_count == 2


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_409_412_timeout(mock_time):
    mock_time.time.side_effect = [0, 100000]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "deactivated"},
    ]
    instance.api.post_dedicated_server_rescue_activate.side_effect = APIError409(
        msg=INCOMPATIBLE_STATE_MSG, api_url="/test", status_code=409
    )

    with pytest.raises(APIError409):
        instance.run()


def test_409_non_feature_state_not_retried():
    """409 with a code other than INCOMPATIBLE_FEATURE_STATE should not be retried."""
    other_msg = '409 Conflict. b\'{"message":"Other error","code":"OTHER_ERROR"}\''
    instance, _mock_api = create_rescue_instance(state="rescue")
    instance.api.get_dedicated_server_features.return_value = [
        {"name": "host_rescue_mode", "status": "deactivated"},
    ]
    instance.api.post_dedicated_server_rescue_activate.side_effect = APIError409(
        msg=other_msg, api_url="/test", status_code=409
    )

    with pytest.raises(APIError409):
        instance.run()

    instance.api.post_dedicated_server_rescue_activate.assert_called_once()


# --- Wait timeout ---


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_wait_timeout(mock_time):
    # time calls: _retry_on_api_error(start), _wait(start), _wait loop(elapsed)
    mock_time.time.side_effect = [0, 0, 100000]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(state="rescue")
    # features calls: activate_rescue(initial check), _wait loop iter 1
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "deactivated"}],
        [{"name": "host_rescue_mode", "status": "activation"}],
    ]
    instance.api.post_dedicated_server_rescue_activate.return_value = {
        "name": "host_rescue_mode",
        "status": "activation",
    }

    with pytest.raises(WaitError) as exc_info:
        instance.run()

    assert "Timeout" in str(exc_info.value.msg)


# --- SSH key resolution ---


def test_ssh_key_name_resolution():
    instance, _mock_api = create_rescue_instance(
        state="rescue",
        auth_methods=["ssh_key"],
        ssh_key_name="my-key",
    )

    instance.api.toolbox.get_ssh_fingerprints_by_key_name.assert_called_once_with(
        "my-key", must=True
    )
    assert instance.ssh_key_fingerprints == [
        instance.api.toolbox.get_ssh_fingerprints_by_key_name.return_value
    ]


@mock.patch(
    "ansible_collections.serverscom.sc_api.plugins.module_utils"
    ".dedicated_server.time"
)
def test_activate_with_ssh_key_fingerprints(mock_time):
    mock_time.time.side_effect = [0, 0, 0, 0]
    mock_time.sleep = mock.MagicMock()

    instance, _mock_api = create_rescue_instance(
        state="rescue",
        auth_methods=["ssh_key"],
        ssh_key_fingerprints=["ab:cd:ef:12:34"],
    )
    instance.api.get_dedicated_server_features.side_effect = [
        [{"name": "host_rescue_mode", "status": "deactivated"}],
        [{"name": "host_rescue_mode", "status": "activated"}],
    ]
    instance.api.post_dedicated_server_rescue_activate.return_value = {
        "name": "host_rescue_mode",
        "status": "activation",
    }
    instance.api.get_dedicated_servers.return_value = dict(RESCUE_SERVER)

    result = instance.run()

    assert result["changed"] is True
    instance.api.post_dedicated_server_rescue_activate.assert_called_once_with(
        "test-server",
        auth_methods=["ssh_key"],
        ssh_key_fingerprints=["ab:cd:ef:12:34"],
    )


# --- auth_methods validation ---


def test_invalid_auth_method():
    with pytest.raises(ModuleError) as exc_info:
        create_rescue_instance(
            state="rescue",
            auth_methods=["password", "invalid"],
        )

    assert "Invalid auth_methods" in str(exc_info.value.msg)
    assert "invalid" in str(exc_info.value.msg)


def test_ssh_key_without_fingerprints_or_name():
    with pytest.raises(ModuleError) as exc_info:
        create_rescue_instance(
            state="rescue",
            auth_methods=["ssh_key"],
        )

    assert "ssh_key_fingerprints or ssh_key_name is required" in str(exc_info.value.msg)
