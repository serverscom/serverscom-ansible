# Copyright (c) 2020 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import pytest
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_dedicated_server import (
    ScDedicatedServerInfo,
)  # noqa


__metaclass__ = type


@pytest.fixture(scope="function")
def module():
    module = mock.MagicMock()
    return module


def test_ready():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powered_on"
    si["status"] = "active"
    assert ScDedicatedServerInfo._is_server_ready(si) is True


def test_not_ready_pending():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powered_on"
    si["status"] = "pending"
    assert ScDedicatedServerInfo._is_server_ready(si) is False


def test_not_ready_off():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powered_off"
    si["status"] = "active"
    assert ScDedicatedServerInfo._is_server_ready(si) is False


def test_not_ready_installing():
    si = {}
    si["operational_status"] = "installation"
    si["power_status"] = "powered_on"
    si["status"] = "active"
    assert ScDedicatedServerInfo._is_server_ready(si) is False
