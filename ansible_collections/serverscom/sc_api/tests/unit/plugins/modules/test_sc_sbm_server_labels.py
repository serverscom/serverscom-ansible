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
    ScSbmServerLabels,
)  # noqa
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    APIError404,
)


__metaclass__ = type


SERVER = {
    "id": "test-server",
    "title": "web-01",
    "status": "active",
    "labels": {"env": "staging"},
}


def create_labels_instance(labels=None, checkmode=False):
    if labels is None:
        labels = {"env": "prod"}
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ):
        return ScSbmServerLabels(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            server_id="test-server",
            labels=labels,
            checkmode=checkmode,
        )


def test_update_labels():
    instance = create_labels_instance(labels={"env": "prod"})
    instance.api.get_sbm_servers.return_value = dict(SERVER)
    updated = dict(SERVER, labels={"env": "prod"})
    instance.api.put_sbm_server.return_value = (200, updated)

    result = instance.run()

    assert result["changed"] is True
    instance.api.put_sbm_server.assert_called_once_with("test-server", {"env": "prod"})


def test_labels_already_match():
    instance = create_labels_instance(labels={"env": "staging"})
    instance.api.get_sbm_servers.return_value = dict(SERVER)

    result = instance.run()

    assert result["changed"] is False
    instance.api.put_sbm_server.assert_not_called()


def test_update_labels_checkmode():
    instance = create_labels_instance(labels={"env": "prod"}, checkmode=True)
    instance.api.get_sbm_servers.return_value = dict(SERVER)

    result = instance.run()

    assert result["changed"] is True
    instance.api.put_sbm_server.assert_not_called()


def test_server_not_found():
    instance = create_labels_instance()
    instance.api.get_sbm_servers.side_effect = APIError404(
        msg="Not found", api_url="/test", status_code=404
    )

    with pytest.raises(ModuleError) as exc_info:
        instance.run()

    assert "not found" in str(exc_info.value.msg)


def test_remove_all_labels():
    instance = create_labels_instance(labels={})
    instance.api.get_sbm_servers.return_value = dict(SERVER)
    updated = dict(SERVER, labels={})
    instance.api.put_sbm_server.return_value = (200, updated)

    result = instance.run()

    assert result["changed"] is True
    instance.api.put_sbm_server.assert_called_once_with("test-server", {})
