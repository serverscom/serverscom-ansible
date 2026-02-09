# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerInfo,
)  # noqa


__metaclass__ = type


def test_ready():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powered_on"
    si["status"] = "active"
    assert ScSbmServerInfo._is_server_ready(si) is True


def test_not_ready_pending():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powered_on"
    si["status"] = "pending"
    assert ScSbmServerInfo._is_server_ready(si) is False


def test_not_ready_off():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powered_off"
    si["status"] = "active"
    assert ScSbmServerInfo._is_server_ready(si) is False


def test_not_ready_installing():
    si = {}
    si["operational_status"] = "installation"
    si["power_status"] = "powered_on"
    si["status"] = "active"
    assert ScSbmServerInfo._is_server_ready(si) is False


def test_not_ready_powering_on():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powering_on"
    si["status"] = "active"
    assert ScSbmServerInfo._is_server_ready(si) is False


def test_not_ready_provisioning():
    si = {}
    si["operational_status"] = "provisioning"
    si["power_status"] = "powered_on"
    si["status"] = "active"
    assert ScSbmServerInfo._is_server_ready(si) is False


def test_not_ready_init_status():
    si = {}
    si["operational_status"] = "normal"
    si["power_status"] = "powered_on"
    si["status"] = "init"
    assert ScSbmServerInfo._is_server_ready(si) is False


def test_not_ready_missing_fields():
    si = {}
    assert ScSbmServerInfo._is_server_ready(si) is False


def test_not_ready_partial_fields():
    si = {"status": "active"}
    assert ScSbmServerInfo._is_server_ready(si) is False
