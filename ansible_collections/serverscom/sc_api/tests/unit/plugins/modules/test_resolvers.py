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
    resolve_sbm_server_id,
    resolve_location_id,
    resolve_sbm_flavor_model_id,
    resolve_operating_system_id,
)


__metaclass__ = type


# ─── resolve_sbm_server_id tests ───


def test_resolve_server_id_passthrough():
    api = mock.MagicMock()
    result = resolve_sbm_server_id(api, server_id="srv123")
    assert result == "srv123"
    api.list_sbm_servers.assert_not_called()


def test_resolve_server_id_by_hostname():
    api = mock.MagicMock()
    api.list_sbm_servers.return_value = iter([{"id": "srv123", "title": "web-01"}])
    result = resolve_sbm_server_id(api, hostname="web-01")
    assert result == "srv123"
    api.list_sbm_servers.assert_called_once_with(search_pattern="web-01")


def test_resolve_server_id_hostname_not_found():
    api = mock.MagicMock()
    api.list_sbm_servers.return_value = iter([])
    with pytest.raises(ModuleError) as exc_info:
        resolve_sbm_server_id(api, hostname="nonexistent")
    assert "not found" in str(exc_info.value.msg)


def test_resolve_server_id_hostname_multiple():
    api = mock.MagicMock()
    api.list_sbm_servers.return_value = iter(
        [
            {"id": "srv1", "title": "web-01"},
            {"id": "srv2", "title": "web-01"},
        ]
    )
    with pytest.raises(ModuleError) as exc_info:
        resolve_sbm_server_id(api, hostname="web-01")
    assert "Multiple" in str(exc_info.value.msg)


def test_resolve_server_id_hostname_filters_exact():
    api = mock.MagicMock()
    api.list_sbm_servers.return_value = iter(
        [
            {"id": "srv1", "title": "web-01-staging"},
            {"id": "srv2", "title": "web-01"},
        ]
    )
    result = resolve_sbm_server_id(api, hostname="web-01")
    assert result == "srv2"


def test_resolve_server_id_both_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_sbm_server_id(api, server_id="srv123", hostname="web-01")
    assert "mutually exclusive" in str(exc_info.value.msg)


def test_resolve_server_id_neither_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_sbm_server_id(api)
    assert "must be provided" in str(exc_info.value.msg)


# ─── resolve_location_id tests ───


def test_resolve_location_id_passthrough():
    api = mock.MagicMock()
    result = resolve_location_id(api, location_id=42)
    assert result == 42
    api.list_locations.assert_not_called()


def test_resolve_location_id_by_code():
    api = mock.MagicMock()
    api.list_locations.return_value = iter([{"id": 42, "code": "AMS7"}])
    result = resolve_location_id(api, location_code="ams7")
    assert result == 42
    api.list_locations.assert_called_once_with(search_pattern="AMS7")


def test_resolve_location_id_code_not_found():
    api = mock.MagicMock()
    api.list_locations.return_value = iter([])
    with pytest.raises(ModuleError) as exc_info:
        resolve_location_id(api, location_code="ZZZZ")
    assert "not found" in str(exc_info.value.msg)


def test_resolve_location_id_both_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_location_id(api, location_id=42, location_code="AMS7")
    assert "mutually exclusive" in str(exc_info.value.msg)


def test_resolve_location_id_neither_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_location_id(api)
    assert "must be provided" in str(exc_info.value.msg)


def test_resolve_location_id_code_filters_exact():
    api = mock.MagicMock()
    api.list_locations.return_value = iter(
        [
            {"id": 10, "code": "AMS77"},
            {"id": 42, "code": "AMS7"},
        ]
    )
    result = resolve_location_id(api, location_code="AMS7")
    assert result == 42


# ─── resolve_sbm_flavor_model_id tests ───


def test_resolve_flavor_id_passthrough():
    api = mock.MagicMock()
    result = resolve_sbm_flavor_model_id(api, 42, sbm_flavor_model_id=100)
    assert result == 100
    api.list_sbm_flavor_models.assert_not_called()


def test_resolve_flavor_id_by_name():
    api = mock.MagicMock()
    api.list_sbm_flavor_models.return_value = iter([{"id": 100, "name": "DL-01"}])
    result = resolve_sbm_flavor_model_id(api, 42, sbm_flavor_model_name="DL-01")
    assert result == 100
    api.list_sbm_flavor_models.assert_called_once_with(42, search_pattern="DL-01")


def test_resolve_flavor_id_name_not_found():
    api = mock.MagicMock()
    api.list_sbm_flavor_models.return_value = iter([])
    with pytest.raises(ModuleError) as exc_info:
        resolve_sbm_flavor_model_id(api, 42, sbm_flavor_model_name="NONEXISTENT")
    assert "not found" in str(exc_info.value.msg)


def test_resolve_flavor_id_both_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_sbm_flavor_model_id(
            api, 42, sbm_flavor_model_id=100, sbm_flavor_model_name="DL-01"
        )
    assert "mutually exclusive" in str(exc_info.value.msg)


def test_resolve_flavor_id_neither_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_sbm_flavor_model_id(api, 42)
    assert "must be provided" in str(exc_info.value.msg)


def test_resolve_flavor_id_name_filters_exact():
    api = mock.MagicMock()
    api.list_sbm_flavor_models.return_value = iter(
        [
            {"id": 100, "name": "DL-01-Extended"},
            {"id": 200, "name": "DL-01"},
        ]
    )
    result = resolve_sbm_flavor_model_id(api, 42, sbm_flavor_model_name="DL-01")
    assert result == 200


# ─── resolve_operating_system_id tests ───


OS_LIST = [
    {"id": 49, "full_name": "Ubuntu 22.04 LTS"},
    {"id": 50, "full_name": "Ubuntu 20.04 LTS"},
    {"id": 51, "full_name": "Debian 11"},
    {"id": 52, "full_name": "CentOS 8"},
]


def test_resolve_os_id_passthrough():
    api = mock.MagicMock()
    result = resolve_operating_system_id(api, 42, 100, operating_system_id=49)
    assert result == 49
    api.list_os_images_by_sbm_flavor_id.assert_not_called()


def test_resolve_os_id_by_name():
    api = mock.MagicMock()
    api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)
    result = resolve_operating_system_id(
        api, 42, 100, operating_system_name="Debian 11"
    )
    assert result == 51


def test_resolve_os_id_by_name_not_found():
    api = mock.MagicMock()
    api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)
    with pytest.raises(ModuleError) as exc_info:
        resolve_operating_system_id(api, 42, 100, operating_system_name="Windows 10")
    assert "not found" in str(exc_info.value.msg)


def test_resolve_os_id_by_regex_single_match():
    api = mock.MagicMock()
    api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)
    result = resolve_operating_system_id(api, 42, 100, operating_system_regex="Debian")
    assert result == 51


def test_resolve_os_id_by_regex_multiple_matches():
    api = mock.MagicMock()
    api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)
    with pytest.raises(ModuleError) as exc_info:
        resolve_operating_system_id(api, 42, 100, operating_system_regex="Ubuntu")
    assert "Multiple OS options match" in str(exc_info.value.msg)


def test_resolve_os_id_by_regex_no_match():
    api = mock.MagicMock()
    api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)
    with pytest.raises(ModuleError) as exc_info:
        resolve_operating_system_id(api, 42, 100, operating_system_regex="Windows")
    assert "No OS options match" in str(exc_info.value.msg)


def test_resolve_os_id_by_regex_invalid():
    api = mock.MagicMock()
    api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)
    with pytest.raises(ModuleError) as exc_info:
        resolve_operating_system_id(api, 42, 100, operating_system_regex="[invalid")
    assert "Invalid operating_system_regex" in str(exc_info.value.msg)


def test_resolve_os_id_empty_os_list():
    api = mock.MagicMock()
    api.list_os_images_by_sbm_flavor_id.return_value = iter([])
    with pytest.raises(ModuleError) as exc_info:
        resolve_operating_system_id(
            api, 42, 100, operating_system_name="Ubuntu 22.04 LTS"
        )
    assert "No available OS options" in str(exc_info.value.msg)


def test_resolve_os_id_multiple_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_operating_system_id(
            api,
            42,
            100,
            operating_system_id=49,
            operating_system_name="Ubuntu 22.04 LTS",
        )
    assert "mutually exclusive" in str(exc_info.value.msg)


def test_resolve_os_id_none_provided():
    api = mock.MagicMock()
    with pytest.raises(ModuleError) as exc_info:
        resolve_operating_system_id(api, 42, 100)
    assert "must be provided" in str(exc_info.value.msg)
