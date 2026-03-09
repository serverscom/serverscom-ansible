# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

import json

import mock
import pytest
from ansible.module_utils import basic

from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
)


__metaclass__ = type

MODULE = "ansible_collections.serverscom.sc_api.plugins.modules.sc_ssh_keys_info"
HANDLER = MODULE.replace(".modules.", ".module_utils.").replace(
    ".sc_ssh_keys_info", ".sc_ssh_key.ScSshKeysInfo"
)


def _set_module_args(args):
    args_json = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = args_json.encode("utf-8")
    basic._ANSIBLE_PROFILE = "legacy"


def _run_module(monkeypatch, module_args, env=None):
    """Run sc_ssh_keys_info.main() and return (token, endpoint) received by handler."""
    env = env or {}
    for key, val in env.items():
        monkeypatch.setenv(key, val)

    _set_module_args(module_args)

    captured = {}

    def fake_init(self, endpoint, token, label_selector):
        captured["token"] = token
        captured["endpoint"] = endpoint

    with mock.patch(HANDLER + ".__init__", fake_init), mock.patch(
        HANDLER + ".run", return_value={"changed": False, "ssh_keys": []}
    ):
        from ansible_collections.serverscom.sc_api.plugins.modules import (
            sc_ssh_keys_info,
        )

        with pytest.raises(SystemExit) as exc_info:
            sc_ssh_keys_info.main()
        assert exc_info.value.code == 0, "Module failed unexpectedly"

    return captured["token"], captured["endpoint"]


def test_token_from_param(monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_TOKEN", raising=False)
    monkeypatch.delenv("SC_TOKEN", raising=False)
    token, _endpoint = _run_module(monkeypatch, {"token": "param-token"})
    assert token == "param-token"


def test_token_param_overrides_env(monkeypatch):
    token, _endpoint = _run_module(
        monkeypatch,
        {"token": "param-token"},
        env={"SERVERSCOM_API_TOKEN": "env-token", "SC_TOKEN": "sc-token"},
    )
    assert token == "param-token"


def test_token_from_serverscom_api_token_env(monkeypatch):
    monkeypatch.delenv("SC_TOKEN", raising=False)
    token, _endpoint = _run_module(
        monkeypatch,
        {},
        env={"SERVERSCOM_API_TOKEN": "env-serverscom"},
    )
    assert token == "env-serverscom"


def test_token_from_sc_token_env(monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_TOKEN", raising=False)
    token, _endpoint = _run_module(
        monkeypatch,
        {},
        env={"SC_TOKEN": "env-sc"},
    )
    assert token == "env-sc"


def test_serverscom_api_token_wins_over_sc_token(monkeypatch):
    token, _endpoint = _run_module(
        monkeypatch,
        {},
        env={"SERVERSCOM_API_TOKEN": "winner", "SC_TOKEN": "loser"},
    )
    assert token == "winner"


def test_endpoint_from_param(monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_URL", raising=False)
    _token, endpoint = _run_module(
        monkeypatch,
        {"token": "t", "endpoint": "https://custom.api/v1"},
    )
    assert endpoint == "https://custom.api/v1"


def test_endpoint_default(monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_URL", raising=False)
    _token, endpoint = _run_module(monkeypatch, {"token": "t"})
    assert endpoint == DEFAULT_API_ENDPOINT


def test_endpoint_from_env(monkeypatch):
    _token, endpoint = _run_module(
        monkeypatch,
        {"token": "t"},
        env={"SERVERSCOM_API_URL": "https://env.api/v1"},
    )
    assert endpoint == "https://env.api/v1"


def test_endpoint_param_overrides_env(monkeypatch):
    _token, endpoint = _run_module(
        monkeypatch,
        {"token": "t", "endpoint": "https://param.api/v1"},
        env={"SERVERSCOM_API_URL": "https://env.api/v1"},
    )
    assert endpoint == "https://param.api/v1"


def test_no_token_fails(monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_TOKEN", raising=False)
    monkeypatch.delenv("SC_TOKEN", raising=False)

    _set_module_args({})

    from ansible_collections.serverscom.sc_api.plugins.modules import sc_ssh_keys_info

    with pytest.raises(SystemExit) as exc_info:
        sc_ssh_keys_info.main()
    assert exc_info.value.code != 0
