# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import pytest
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server import (
    ScDedicatedServerIpxe,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    WaitError,
)


__metaclass__ = type

ENDPOINT = "https://api.servers.com/v1"
TOKEN = "test-token"
SERVER_ID = "srv123"


def _make_feature(name, status, ipxe_config=None):
    f = {"name": name, "status": status}
    if ipxe_config is not None:
        f["ipxe_config"] = ipxe_config
    return f


def _make_handler(ipxe_type="public", state="present", ipxe_config=None,
                  wait=0, update_interval=10, checkmode=False):
    return ScDedicatedServerIpxe(
        endpoint=ENDPOINT,
        token=TOKEN,
        server_id=SERVER_ID,
        ipxe_type=ipxe_type,
        state=state,
        ipxe_config=ipxe_config,
        wait=wait,
        update_interval=update_interval,
        checkmode=checkmode,
    )


class TestActivate:
    def test_activate_public_ipxe(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        features = [
            _make_feature("public_ipxe_boot", "deactivated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features
        handler.api.post_dedicated_server_feature_activate.return_value = (
            _make_feature("public_ipxe_boot", "activation")
        )

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_activate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot",
            body={"ipxe_config": "#!ipxe\nchain http://boot.example.com"},
        )

    def test_activate_private_ipxe(self):
        handler = _make_handler(
            ipxe_type="private", state="present",
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        features = [
            _make_feature("public_ipxe_boot", "deactivated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features
        handler.api.post_dedicated_server_feature_activate.return_value = (
            _make_feature("private_ipxe_boot", "activation")
        )

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_activate.assert_called_once_with(
            SERVER_ID, "private_ipxe_boot",
            body={"ipxe_config": "#!ipxe\nchain http://boot.example.com"},
        )

    def test_activate_with_ipxe_config(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="#!ipxe\nchain http://boot.example.com"
        )
        features = [_make_feature("public_ipxe_boot", "deactivated")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_activate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot",
            body={"ipxe_config": "#!ipxe\nchain http://boot.example.com"},
        )

    def test_activate_already_active_same_config(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="existing-config",
        )
        features = [
            _make_feature("public_ipxe_boot", "activated", ipxe_config="existing-config")
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features
        handler.api.get_dedicated_servers.return_value = {"ipxe_config": "existing-config"}

        result = handler.run()

        assert result["changed"] is False
        handler.api.put_dedicated_server.assert_not_called()

    def test_activate_already_active_with_config_update(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="#!ipxe\nnew-config"
        )
        features = [
            _make_feature("public_ipxe_boot", "activated", ipxe_config="old-config")
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features
        handler.api.get_dedicated_servers.return_value = {"ipxe_config": "old-config"}

        result = handler.run()

        assert result["changed"] is True
        handler.api.put_dedicated_server.assert_called_once_with(
            SERVER_ID, {"ipxe_config": "#!ipxe\nnew-config"}
        )
        handler.api.post_dedicated_server_feature_activate.assert_not_called()

    def test_activate_already_active_config_unchanged(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="same-config"
        )
        features = [
            _make_feature("public_ipxe_boot", "activated", ipxe_config="same-config")
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features
        handler.api.get_dedicated_servers.return_value = {"ipxe_config": "same-config"}

        result = handler.run()

        assert result["changed"] is False
        handler.api.put_dedicated_server.assert_not_called()

    def test_activate_from_incompatible(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        features = [_make_feature("public_ipxe_boot", "incompatible")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_activate.assert_called_once()

    def test_activate_from_unavailable(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        features = [_make_feature("public_ipxe_boot", "unavailable")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_activate.assert_called_once()

    def test_activate_already_in_activation(self):
        handler = _make_handler(
            ipxe_type="public", state="present",
            ipxe_config="#!ipxe\nchain http://boot.example.com",
            wait=0,
        )
        features = [_make_feature("public_ipxe_boot", "activation")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False
        handler.api.post_dedicated_server_feature_activate.assert_not_called()


class TestDeactivate:
    def test_deactivate_ipxe(self):
        handler = _make_handler(state="absent")
        features = [_make_feature("public_ipxe_boot", "activated")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot"
        )

    def test_deactivate_already_inactive(self):
        handler = _make_handler(state="absent")
        features = [_make_feature("public_ipxe_boot", "deactivated")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()

    def test_deactivate_already_in_deactivation(self):
        handler = _make_handler(state="absent", wait=0)
        features = [_make_feature("public_ipxe_boot", "deactivation")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()

    def test_deactivate_incompatible(self):
        handler = _make_handler(state="absent")
        features = [_make_feature("public_ipxe_boot", "incompatible")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False

    def test_deactivate_unavailable(self):
        handler = _make_handler(state="absent")
        features = [_make_feature("public_ipxe_boot", "unavailable")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False


class TestCheckMode:
    def test_activate_checkmode(self):
        handler = _make_handler(
            state="present", checkmode=True,
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        features = [_make_feature("public_ipxe_boot", "deactivated")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_activate.assert_not_called()

    def test_activate_checkmode_already_active_same_config(self):
        """In check mode with matching ipxe_config, changed=False."""
        handler = _make_handler(
            state="present", checkmode=True,
            ipxe_config="existing-config",
        )
        features = [
            _make_feature("public_ipxe_boot", "activated", ipxe_config="existing-config")
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features
        handler.api.get_dedicated_servers.return_value = {"ipxe_config": "existing-config"}

        result = handler.run()

        assert result["changed"] is False
        handler.api.put_dedicated_server.assert_not_called()

    def test_activate_checkmode_with_different_config(self):
        handler = _make_handler(
            state="present", checkmode=True, ipxe_config="new"
        )
        features = [_make_feature("public_ipxe_boot", "activated")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features
        handler.api.get_dedicated_servers.return_value = {"ipxe_config": "old"}

        result = handler.run()

        assert result["changed"] is True
        handler.api.put_dedicated_server.assert_not_called()

    def test_deactivate_checkmode(self):
        handler = _make_handler(state="absent", checkmode=True)
        features = [_make_feature("public_ipxe_boot", "activated")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()

    def test_deactivate_checkmode_already_inactive(self):
        handler = _make_handler(state="absent", checkmode=True)
        features = [_make_feature("public_ipxe_boot", "deactivated")]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False


class TestWait:
    @mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server.time")
    def test_wait_for_activation(self, mock_time):
        mock_time.time.side_effect = [0, 0, 5, 5, 10]
        mock_time.sleep = mock.MagicMock()

        handler = _make_handler(
            state="present", wait=60, update_interval=5,
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            [_make_feature("public_ipxe_boot", "deactivated")],
            [_make_feature("public_ipxe_boot", "activation")],
            [_make_feature("public_ipxe_boot", "activated")],
        ]

        result = handler.run()

        assert result["changed"] is True
        assert result["feature"]["status"] == "activated"
        assert handler.api.post_dedicated_server_feature_activate.call_count == 1

    @mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server.time")
    def test_wait_for_deactivation(self, mock_time):
        mock_time.time.side_effect = [0, 0, 5, 5, 10]
        mock_time.sleep = mock.MagicMock()

        handler = _make_handler(state="absent", wait=60, update_interval=5)
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            [_make_feature("public_ipxe_boot", "activated")],
            [_make_feature("public_ipxe_boot", "deactivation")],
            [_make_feature("public_ipxe_boot", "deactivated")],
        ]

        result = handler.run()

        assert result["changed"] is True
        assert result["feature"]["status"] == "deactivated"

    @mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server.time")
    def test_wait_timeout(self, mock_time):
        # time.time() calls: start=0, loop1_check=1, loop1_retry=2, loop2_check=601
        mock_time.time.side_effect = [0, 1, 2, 601]
        mock_time.sleep = mock.MagicMock()

        handler = _make_handler(
            state="present", wait=600, update_interval=10,
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            [_make_feature("public_ipxe_boot", "deactivated")],
            [_make_feature("public_ipxe_boot", "activation")],
        ]

        with pytest.raises(WaitError):
            handler.run()
