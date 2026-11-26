# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import pytest
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server import (
    ScDedicatedOSList,
)


__metaclass__ = type

MODEL_NAME = 'Dell R470 / Intel Xeon 6511P - 8x2.5" / 64 GB RAM'


def make_os_list(server_model_name, models):
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server.ScApi"
    ) as api_cls:
        api = api_cls.return_value
        api.list_server_models.return_value = models
        api.list_os_images_by_model_id.return_value = [
            {"id": 1, "full_name": "Debian 13 x86_64"}
        ]
        os_list = ScDedicatedOSList(
            endpoint="https://example.com",
            token="token",
            server_id=None,
            location_id=34,
            location_code=None,
            server_model_id=None,
            server_model_name=server_model_name,
            os_name_regex=None,
        )
    return os_list, api


def test_model_name_exact_match():
    os_list, api = make_os_list(MODEL_NAME, [{"id": 19427, "name": MODEL_NAME}])
    result = os_list.run()
    assert result["os_list"] == [{"id": 1, "full_name": "Debian 13 x86_64"}]
    api.list_os_images_by_model_id.assert_called_once_with(34, 19427)


def test_model_name_api_trailing_space():
    os_list, api = make_os_list(
        MODEL_NAME, [{"id": 19427, "name": MODEL_NAME + " "}]
    )
    os_list.run()
    api.list_os_images_by_model_id.assert_called_once_with(34, 19427)


def test_model_name_user_whitespace():
    os_list, api = make_os_list(
        " " + MODEL_NAME + " ", [{"id": 19427, "name": MODEL_NAME}]
    )
    os_list.run()
    api.list_server_models.assert_called_once_with(34, search_pattern=MODEL_NAME)
    api.list_os_images_by_model_id.assert_called_once_with(34, 19427)


def test_model_name_partial_not_matched():
    os_list, api = make_os_list("Dell R470", [{"id": 19427, "name": MODEL_NAME}])
    with pytest.raises(ModuleError):
        os_list.run()
    api.list_os_images_by_model_id.assert_not_called()
