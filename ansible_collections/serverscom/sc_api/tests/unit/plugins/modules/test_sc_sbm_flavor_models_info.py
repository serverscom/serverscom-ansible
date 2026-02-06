# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmFlavorModelsInfo,
)  # noqa


__metaclass__ = type


FLAVOR_MODELS = [
    {
        "id": 1,
        "name": "SBM-Small",
        "cpu_description": "4 cores",
        "ram_size": 8192,
        "drives_description": "100GB SSD",
    },
    {
        "id": 2,
        "name": "SBM-Medium",
        "cpu_description": "8 cores",
        "ram_size": 16384,
        "drives_description": "200GB SSD",
    },
    {
        "id": 3,
        "name": "SBM-Large",
        "cpu_description": "16 cores",
        "ram_size": 32768,
        "drives_description": "500GB SSD",
    },
]


def test_run_returns_flavor_models():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_flavor_models.return_value = iter(FLAVOR_MODELS)

        info = ScSbmFlavorModelsInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            location_id=1,
            search_pattern=None,
        )
        result = info.run()

        assert result["changed"] is False
        assert result["sbm_flavor_models"] == FLAVOR_MODELS
        mock_instance.list_sbm_flavor_models.assert_called_once_with(1, None)


def test_run_with_search_pattern():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_flavor_models.return_value = iter([FLAVOR_MODELS[1]])

        info = ScSbmFlavorModelsInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            location_id=1,
            search_pattern="Medium",
        )
        result = info.run()

        assert result["changed"] is False
        assert len(result["sbm_flavor_models"]) == 1
        assert result["sbm_flavor_models"][0]["name"] == "SBM-Medium"
        mock_instance.list_sbm_flavor_models.assert_called_once_with(1, "Medium")


def test_run_empty_result():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.list_sbm_flavor_models.return_value = iter([])

        info = ScSbmFlavorModelsInfo(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            location_id=999,
            search_pattern=None,
        )
        result = info.run()

        assert result["changed"] is False
        assert result["sbm_flavor_models"] == []
