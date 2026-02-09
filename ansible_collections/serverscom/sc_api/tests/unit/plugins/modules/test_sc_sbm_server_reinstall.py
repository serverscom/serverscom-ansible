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
    ScSbmServerReinstall,
)  # noqa


__metaclass__ = type


SERVER_DATA = {
    "id": "test-server",
    "title": "my-sbm-server",
    "status": "active",
    "power_status": "powered_on",
    "operational_status": "normal",
    "location_id": 1,
    "location_code": "NYC",
    "configuration_details": {
        "sbm_flavor_model_id": 100,
        "sbm_flavor_model_name": "SBM-Test",
        "operating_system_id": 49,
        "operating_system_full_name": "Ubuntu 22.04 LTS",
    },
}

OS_LIST = [
    {"id": 49, "full_name": "Ubuntu 22.04 LTS"},
    {"id": 50, "full_name": "Ubuntu 20.04 LTS"},
    {"id": 51, "full_name": "Debian 11"},
    {"id": 52, "full_name": "CentOS 8"},
]


@pytest.fixture
def mock_api():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.get_sbm_servers.return_value = SERVER_DATA.copy()
        mock_instance.list_os_images_by_sbm_flavor_id.return_value = OS_LIST
        mock_instance.toolbox.get_ssh_fingerprints_by_key_name.return_value = (
            "aa:bb:cc:dd"
        )
        yield mock_instance


def test_get_hostname_provided(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="custom-hostname",
        operating_system_id=49,
        operating_system_regex=None,
        ssh_keys=None,
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.hostname == "custom-hostname"


def test_get_hostname_from_server(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname=None,
        operating_system_id=49,
        operating_system_regex=None,
        ssh_keys=None,
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.hostname == "my-sbm-server"


def test_get_operating_system_id_provided(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="test",
        operating_system_id=51,
        operating_system_regex=None,
        ssh_keys=None,
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.operating_system_id == 51


def test_get_operating_system_id_from_server(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="test",
        operating_system_id=None,
        operating_system_regex=None,
        ssh_keys=None,
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.operating_system_id == 49


def test_get_operating_system_id_by_regex(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="test",
        operating_system_id=None,
        operating_system_regex="Debian",
        ssh_keys=None,
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.operating_system_id == 51


def test_get_operating_system_id_by_regex_multiple_matches(mock_api):
    with pytest.raises(ModuleError) as exc_info:
        ScSbmServerReinstall(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            hostname="test",
            operating_system_id=None,
            operating_system_regex="Ubuntu",
            ssh_keys=None,
            ssh_key_name=None,
            user_data=None,
            wait=0,
            update_interval=60,
            checkmode=True,
        )
    assert "Multiple OS options match" in str(exc_info.value.msg)


def test_get_operating_system_id_by_regex_no_match(mock_api):
    with pytest.raises(ModuleError) as exc_info:
        ScSbmServerReinstall(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            hostname="test",
            operating_system_id=None,
            operating_system_regex="Windows",
            ssh_keys=None,
            ssh_key_name=None,
            user_data=None,
            wait=0,
            update_interval=60,
            checkmode=True,
        )
    assert "No OS options match" in str(exc_info.value.msg)


def test_get_ssh_keys_provided(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="test",
        operating_system_id=49,
        operating_system_regex=None,
        ssh_keys=["aa:bb:cc:dd", "ee:ff:00:11"],
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.ssh_keys == ["aa:bb:cc:dd", "ee:ff:00:11"]


def test_get_ssh_keys_by_name(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="test",
        operating_system_id=49,
        operating_system_regex=None,
        ssh_keys=None,
        ssh_key_name="my-key",
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.ssh_keys == ["aa:bb:cc:dd"]


def test_get_ssh_keys_empty(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="test",
        operating_system_id=49,
        operating_system_regex=None,
        ssh_keys=None,
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    assert reinstall.ssh_keys == []


def test_run_checkmode(mock_api):
    reinstall = ScSbmServerReinstall(
        endpoint="https://api.servers.com/v1",
        token="test-token",
        server_id="test-server",
        hostname="test",
        operating_system_id=49,
        operating_system_regex=None,
        ssh_keys=None,
        ssh_key_name=None,
        user_data=None,
        wait=0,
        update_interval=60,
        checkmode=True,
    )
    result = reinstall.run()
    assert result["changed"] is True
    mock_api.post_sbm_server_reinstall.assert_not_called()


def test_wait_interval_validation(mock_api):
    with pytest.raises(ModuleError) as exc_info:
        ScSbmServerReinstall(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            hostname="test",
            operating_system_id=49,
            operating_system_regex=None,
            ssh_keys=None,
            ssh_key_name=None,
            user_data=None,
            wait=30,
            update_interval=60,
            checkmode=True,
        )
    assert "Update interval" in str(exc_info.value.msg)


@mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.time")
def test_wait_for_server_passes_retry_rules(mock_time):
    mock_time.time.side_effect = [0, 0]
    mock_time.sleep = mock.MagicMock()

    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.get_sbm_servers.side_effect = [
            SERVER_DATA.copy(),  # get_server_data
            {  # wait_for_server poll
                "id": "test-server",
                "status": "active",
                "power_status": "powered_on",
                "operational_status": "normal",
            },
        ]
        mock_instance.toolbox.get_ssh_fingerprints_by_key_name.return_value = (
            "aa:bb:cc:dd"
        )
        mock_instance.post_sbm_server_reinstall.return_value = {"id": "test-server"}

        reinstall = ScSbmServerReinstall(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            hostname=None,
            operating_system_id=49,
            operating_system_regex=None,
            ssh_keys=None,
            ssh_key_name=None,
            user_data=None,
            wait=600,
            update_interval=30,
            checkmode=False,
        )

        reinstall.run()

        call = mock_instance.get_sbm_servers.call_args
        assert "retry_rules" in call.kwargs
        assert call.kwargs["retry_rules"]["codes"] == {429, 500}
