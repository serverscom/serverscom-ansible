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
    ScSbmOSList,
)  # noqa


__metaclass__ = type


OS_LIST = [
    {"id": 49, "full_name": "Ubuntu 22.04 LTS"},
    {"id": 50, "full_name": "Ubuntu 20.04 LTS"},
    {"id": 51, "full_name": "Debian 11"},
    {"id": 52, "full_name": "CentOS 8"},
]

FLAVOR_MODELS = [
    {"id": 100, "name": "DL-01"},
    {"id": 200, "name": "DL-01-Extended"},
]


def create_os_list_instance(
    sbm_flavor_model_id=None,
    sbm_flavor_model_name=None,
    os_name_regex=None,
):
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ):
        return ScSbmOSList(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            location_id=42,
            sbm_flavor_model_id=sbm_flavor_model_id,
            sbm_flavor_model_name=sbm_flavor_model_name,
            os_name_regex=os_name_regex,
        )


def test_run_by_flavor_id():
    instance = create_os_list_instance(sbm_flavor_model_id="100")
    instance.api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)

    result = instance.run()

    assert result["changed"] is False
    assert result["os_list"] == OS_LIST
    instance.api.list_os_images_by_sbm_flavor_id.assert_called_once_with(42, "100")


def test_run_by_flavor_name():
    instance = create_os_list_instance(sbm_flavor_model_name="DL-01")
    instance.api.list_sbm_flavor_models.return_value = iter(FLAVOR_MODELS)
    instance.api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)

    result = instance.run()

    assert result["changed"] is False
    assert result["os_list"] == OS_LIST
    instance.api.list_sbm_flavor_models.assert_called_once_with(
        42, search_pattern="DL-01"
    )
    instance.api.list_os_images_by_sbm_flavor_id.assert_called_once_with(42, 100)


def test_run_by_flavor_name_not_found():
    instance = create_os_list_instance(sbm_flavor_model_name="NONEXISTENT")
    instance.api.list_sbm_flavor_models.return_value = iter([])

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "not found" in str(exc_info.value.msg)


def test_run_with_os_name_regex():
    instance = create_os_list_instance(
        sbm_flavor_model_id="100", os_name_regex="Ubuntu"
    )
    instance.api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)

    result = instance.run()

    assert result["changed"] is False
    assert len(result["os_list"]) == 2
    assert all("Ubuntu" in os["full_name"] for os in result["os_list"])


def test_run_with_os_name_regex_no_match():
    instance = create_os_list_instance(
        sbm_flavor_model_id="100", os_name_regex="Windows"
    )
    instance.api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)

    result = instance.run()

    assert result["changed"] is False
    assert result["os_list"] == []


def test_run_neither_id_nor_name():
    instance = create_os_list_instance()

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "must be provided" in str(exc_info.value.msg)


def test_run_empty_result():
    instance = create_os_list_instance(sbm_flavor_model_id="100")
    instance.api.list_os_images_by_sbm_flavor_id.return_value = iter([])

    result = instance.run()

    assert result["changed"] is False
    assert result["os_list"] == []


def test_run_flavor_name_exact_match():
    """Ensure exact name match, not substring."""
    instance = create_os_list_instance(sbm_flavor_model_name="DL-01")
    instance.api.list_sbm_flavor_models.return_value = iter(FLAVOR_MODELS)
    instance.api.list_os_images_by_sbm_flavor_id.return_value = iter(OS_LIST)

    instance.run()

    # Should use id=100 (DL-01), not id=200 (DL-01-Extended)
    instance.api.list_os_images_by_sbm_flavor_id.assert_called_once_with(42, 100)
