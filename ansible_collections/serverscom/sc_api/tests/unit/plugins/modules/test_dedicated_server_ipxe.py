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


def _make_handler(state="public", ipxe_config=None,
                  wait=0, update_interval=10, checkmode=False):
    return ScDedicatedServerIpxe(
        endpoint=ENDPOINT,
        token=TOKEN,
        server_id=SERVER_ID,
        state=state,
        ipxe_config=ipxe_config,
        wait=wait,
        update_interval=update_interval,
        checkmode=checkmode,
    )


class TestActivate:
    def test_activate_public_ipxe(self):
        handler = _make_handler(
            state="public",
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
            state="private",
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
            state="public",
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
            state="public",
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
            state="public",
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
            state="public",
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
            state="public",
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
            state="public",
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
            state="public",
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
    def test_deactivate_public_active(self):
        handler = _make_handler(state="absent")
        features = [
            _make_feature("public_ipxe_boot", "activated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot"
        )

    def test_deactivate_private_active(self):
        handler = _make_handler(state="absent")
        features = [
            _make_feature("public_ipxe_boot", "deactivated"),
            _make_feature("private_ipxe_boot", "activated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "private_ipxe_boot"
        )

    def test_deactivate_both_already_inactive(self):
        handler = _make_handler(state="absent")
        features = [
            _make_feature("public_ipxe_boot", "deactivated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()

    def test_deactivate_already_in_deactivation(self):
        handler = _make_handler(state="absent", wait=0)
        features = [
            _make_feature("public_ipxe_boot", "deactivation"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()

    def test_deactivate_incompatible(self):
        handler = _make_handler(state="absent")
        features = [
            _make_feature("public_ipxe_boot", "incompatible"),
            _make_feature("private_ipxe_boot", "incompatible"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False

    def test_deactivate_unavailable(self):
        handler = _make_handler(state="absent")
        features = [
            _make_feature("public_ipxe_boot", "unavailable"),
            _make_feature("private_ipxe_boot", "unavailable"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False

    def test_deactivate_feature_in_activation(self):
        """If a feature is being activated, absent should wait then deactivate."""
        handler = _make_handler(state="absent", wait=0)
        features = [
            _make_feature("public_ipxe_boot", "activation"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot"
        )


class TestCheckMode:
    def test_activate_checkmode(self):
        handler = _make_handler(
            state="public", checkmode=True,
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
            state="public", checkmode=True,
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
            state="public", checkmode=True, ipxe_config="new"
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
        features = [
            _make_feature("public_ipxe_boot", "activated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()

    def test_deactivate_checkmode_already_inactive(self):
        handler = _make_handler(state="absent", checkmode=True)
        features = [
            _make_feature("public_ipxe_boot", "deactivated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = features

        result = handler.run()

        assert result["changed"] is False


class TestModeSwitch:
    def test_switch_public_to_private(self):
        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            # _get_feature_status: private deactivated
            [
                _make_feature("public_ipxe_boot", "activated"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # _get_opposite_feature_status: public activated
            [
                _make_feature("public_ipxe_boot", "activated"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
        ]

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot"
        )
        handler.api.post_dedicated_server_feature_activate.assert_called_once_with(
            SERVER_ID, "private_ipxe_boot",
            body={"ipxe_config": "#!ipxe\nchain http://boot.example.com"},
        )

    def test_switch_private_to_public(self):
        handler = _make_handler(
            state="public",
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            # _get_feature_status: public deactivated
            [
                _make_feature("public_ipxe_boot", "deactivated"),
                _make_feature("private_ipxe_boot", "activated"),
            ],
            # _get_opposite_feature_status: private activated
            [
                _make_feature("public_ipxe_boot", "deactivated"),
                _make_feature("private_ipxe_boot", "activated"),
            ],
        ]

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "private_ipxe_boot"
        )
        handler.api.post_dedicated_server_feature_activate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot",
            body={"ipxe_config": "#!ipxe\nchain http://boot.example.com"},
        )

    @mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server.time")
    def test_switch_opposite_in_deactivation(self, mock_time):
        mock_time.time.side_effect = [
            # wait_for_status("deactivated") for opposite
            0, 0, 5, 5, 10,
            # wait_for_status("activated") for private
            10, 10, 15,
        ]
        mock_time.sleep = mock.MagicMock()

        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\ntest", wait=60, update_interval=5,
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            # _get_feature_status: private deactivated
            [
                _make_feature("public_ipxe_boot", "deactivation"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # _get_opposite_feature_status: public in deactivation
            [
                _make_feature("public_ipxe_boot", "deactivation"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # wait_for_status poll for public: still deactivating
            [
                _make_feature("public_ipxe_boot", "deactivation"),
            ],
            # wait_for_status poll for public: done
            [
                _make_feature("public_ipxe_boot", "deactivated"),
            ],
            # wait_for_status poll for private: activated
            [
                _make_feature("private_ipxe_boot", "activated"),
            ],
        ]

        result = handler.run()

        assert result["changed"] is True
        assert result["feature"]["status"] == "activated"
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()
        handler.api.post_dedicated_server_feature_activate.assert_called_once_with(
            SERVER_ID, "private_ipxe_boot", body={"ipxe_config": "#!ipxe\ntest"},
        )

    def test_switch_opposite_in_deactivation_no_wait(self):
        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\ntest", wait=0,
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            [
                _make_feature("public_ipxe_boot", "deactivation"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # _get_feature_status re-fetch
            [
                _make_feature("public_ipxe_boot", "deactivation"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
        ]

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()
        handler.api.post_dedicated_server_feature_activate.assert_called_once()

    def test_switch_with_wait_zero(self):
        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\ntest", wait=0,
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            # _get_feature_status: private deactivated
            [
                _make_feature("public_ipxe_boot", "activated"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # _get_opposite_feature_status: public activated
            [
                _make_feature("public_ipxe_boot", "activated"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
        ]

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot"
        )
        handler.api.post_dedicated_server_feature_activate.assert_called_once()

    def test_switch_checkmode(self):
        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\ntest", checkmode=True,
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = [
            _make_feature("public_ipxe_boot", "activated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()
        handler.api.post_dedicated_server_feature_activate.assert_not_called()

    @mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server.time")
    def test_switch_with_wait_full_cycle(self, mock_time):
        mock_time.time.side_effect = [
            # _deactivate_opposite wait_for_status: start, elapsed, sleep, elapsed
            0, 0, 5, 5, 10,
            # _ensure_present wait_for_status: start, elapsed, sleep, elapsed
            10, 10, 15, 15, 20,
        ]
        mock_time.sleep = mock.MagicMock()

        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\ntest", wait=60, update_interval=5,
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            # _get_feature_status: private deactivated
            [
                _make_feature("public_ipxe_boot", "activated"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # _get_opposite_feature_status: public activated
            [
                _make_feature("public_ipxe_boot", "activated"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # wait for public deactivation: still deactivating
            [
                _make_feature("public_ipxe_boot", "deactivation"),
            ],
            # wait for public deactivation: done
            [
                _make_feature("public_ipxe_boot", "deactivated"),
            ],
            # wait for private activation: still activating
            [
                _make_feature("private_ipxe_boot", "activation"),
            ],
            # wait for private activation: done
            [
                _make_feature("private_ipxe_boot", "activated"),
            ],
        ]

        result = handler.run()

        assert result["changed"] is True
        assert result["feature"]["status"] == "activated"
        handler.api.post_dedicated_server_feature_deactivate.assert_called_once_with(
            SERVER_ID, "public_ipxe_boot"
        )
        handler.api.post_dedicated_server_feature_activate.assert_called_once_with(
            SERVER_ID, "private_ipxe_boot", body={"ipxe_config": "#!ipxe\ntest"},
        )

    def test_no_switch_when_opposite_deactivated(self):
        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\ntest",
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = [
            _make_feature("public_ipxe_boot", "deactivated"),
            _make_feature("private_ipxe_boot", "deactivated"),
        ]

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()
        handler.api.post_dedicated_server_feature_activate.assert_called_once()

    def test_no_switch_when_opposite_not_in_features(self):
        handler = _make_handler(
            state="private",
            ipxe_config="#!ipxe\ntest",
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.return_value = [
            _make_feature("private_ipxe_boot", "deactivated"),
        ]

        result = handler.run()

        assert result["changed"] is True
        handler.api.post_dedicated_server_feature_deactivate.assert_not_called()
        handler.api.post_dedicated_server_feature_activate.assert_called_once()


class TestWait:
    @mock.patch("ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server.time")
    def test_wait_for_activation(self, mock_time):
        mock_time.time.side_effect = [0, 0, 5, 5, 10]
        mock_time.sleep = mock.MagicMock()

        handler = _make_handler(
            state="public", wait=60, update_interval=5,
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
            # initial call in _ensure_absent
            [
                _make_feature("public_ipxe_boot", "activated"),
                _make_feature("private_ipxe_boot", "deactivated"),
            ],
            # wait poll: deactivating
            [_make_feature("public_ipxe_boot", "deactivation")],
            # wait poll: done
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
            state="public", wait=600, update_interval=10,
            ipxe_config="#!ipxe\nchain http://boot.example.com",
        )
        handler.api = mock.MagicMock()
        handler.api.get_dedicated_server_features.side_effect = [
            # _get_feature_status
            [_make_feature("public_ipxe_boot", "deactivated")],
            # _get_opposite_feature_status (no opposite found)
            [_make_feature("public_ipxe_boot", "deactivated")],
            # wait poll: still activating
            [_make_feature("public_ipxe_boot", "activation")],
        ]

        with pytest.raises(WaitError):
            handler.run()
