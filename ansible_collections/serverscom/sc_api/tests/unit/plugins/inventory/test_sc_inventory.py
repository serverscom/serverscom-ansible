# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
import mock

from ansible.errors import AnsibleError, AnsibleParserError

from ansible_collections.serverscom.sc_api.plugins.inventory.sc_inventory import (
    InventoryModule,
)


# ------------------------------------------------------------------- #
# Fixtures
# ------------------------------------------------------------------- #


def _make_baremetal(
    id_="bm1",
    title="bm-host-1",
    location_code="AMS1",
    status="active",
    public="1.1.1.1",
    private="10.0.0.1",
    oob="192.168.0.1",
    labels=None,
    type_="dedicated_server",
):
    return {
        "id": id_,
        "title": title,
        "type": type_,
        "status": status,
        "location_code": location_code,
        "public_ipv4_address": public,
        "private_ipv4_address": private,
        "oob_ipv4_address": oob,
        "labels": labels or {},
    }


def _make_cloud(
    id_="c1",
    name="cloud-host-1",
    region_code="ams1",
    status="ACTIVE",
    public="2.2.2.2",
    private="10.1.0.1",
    public6="2001:db8::1",
    local="172.16.0.1",
    labels=None,
):
    return {
        "id": id_,
        "name": name,
        "status": status,
        "region_code": region_code,
        "public_ipv4_address": public,
        "private_ipv4_address": private,
        "public_ipv6_address": public6,
        "local_ipv4_address": local,
        "labels": labels or {},
    }


@pytest.fixture
def plugin():
    p = InventoryModule()
    p.inventory = mock.MagicMock()
    return p


# ------------------------------------------------------------------- #
# verify_file
# ------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/tmp/x.sc_api.yml", True),
        ("/tmp/x.sc_api.yaml", True),
        ("/tmp/x.sc_inventory.yml", True),
        ("/tmp/x.sc_inventory.yaml", True),
        ("/tmp/x.yml", False),
        ("/tmp/x.aws_ec2.yml", False),
    ],
)
def test_verify_file(plugin, path, expected):
    with mock.patch.object(
        InventoryModule.__bases__[0], "verify_file", return_value=True
    ):
        assert plugin.verify_file(path) is expected


def test_verify_file_super_false(plugin):
    with mock.patch.object(
        InventoryModule.__bases__[0], "verify_file", return_value=False
    ):
        assert plugin.verify_file("/tmp/x.sc_api.yml") is False


# ------------------------------------------------------------------- #
# _substitute_env_vars
# ------------------------------------------------------------------- #


def test_subst_string(plugin, monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    assert plugin._substitute_env_vars("x=${FOO}") == "x=bar"


def test_subst_list(plugin, monkeypatch):
    monkeypatch.setenv("R", "AMS1")
    assert plugin._substitute_env_vars(["${R}", "FRA1"]) == ["AMS1", "FRA1"]


def test_subst_dict(plugin, monkeypatch):
    monkeypatch.setenv("E", "prod")
    assert plugin._substitute_env_vars({"env": "${E}", "x": 1}) == {
        "env": "prod",
        "x": 1,
    }


def test_subst_nested(plugin, monkeypatch):
    monkeypatch.setenv("R", "AMS1")
    monkeypatch.setenv("E", "prod")
    result = plugin._substitute_env_vars(
        {"regions": ["${R}"], "labels": {"env": "${E}"}}
    )
    assert result == {"regions": ["AMS1"], "labels": {"env": "prod"}}


def test_subst_missing_raises(plugin, monkeypatch):
    monkeypatch.delenv("MISSING_FOO", raising=False)
    with pytest.raises(AnsibleParserError, match="MISSING_FOO"):
        plugin._substitute_env_vars("${MISSING_FOO}")


def test_subst_passthrough_non_string(plugin):
    assert plugin._substitute_env_vars(42) == 42
    assert plugin._substitute_env_vars(None) is None
    assert plugin._substitute_env_vars(True) is True


# ------------------------------------------------------------------- #
# Token / endpoint resolution
# ------------------------------------------------------------------- #


def test_token_from_option(plugin, monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_TOKEN", raising=False)
    monkeypatch.delenv("SC_TOKEN", raising=False)
    plugin.get_option = mock.MagicMock(
        side_effect=lambda k: {"token": "T", "endpoint": "https://e"}[k]
    )
    token, endpoint = plugin._resolve_token_endpoint()
    assert token == "T"
    assert endpoint == "https://e"


def test_token_from_servers_env(plugin, monkeypatch):
    monkeypatch.setenv("SERVERSCOM_API_TOKEN", "ENV_TOKEN")
    monkeypatch.delenv("SC_TOKEN", raising=False)
    plugin.get_option = mock.MagicMock(
        side_effect=lambda k: {"token": None, "endpoint": None}[k]
    )
    monkeypatch.delenv("SERVERSCOM_API_URL", raising=False)
    token, endpoint = plugin._resolve_token_endpoint()
    assert token == "ENV_TOKEN"
    assert endpoint == "https://api.servers.com/v1"


def test_token_from_sc_token_fallback(plugin, monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_TOKEN", raising=False)
    monkeypatch.setenv("SC_TOKEN", "OLD_TOKEN")
    plugin.get_option = mock.MagicMock(
        side_effect=lambda k: {"token": None, "endpoint": "https://e"}[k]
    )
    token, _endpoint = plugin._resolve_token_endpoint()
    assert token == "OLD_TOKEN"


def test_no_token_raises(plugin, monkeypatch):
    monkeypatch.delenv("SERVERSCOM_API_TOKEN", raising=False)
    monkeypatch.delenv("SC_TOKEN", raising=False)
    plugin.get_option = mock.MagicMock(
        side_effect=lambda k: {"token": None, "endpoint": None}[k]
    )
    with pytest.raises(AnsibleError, match="No API token"):
        plugin._resolve_token_endpoint()


def test_endpoint_env_fallback(plugin, monkeypatch):
    monkeypatch.setenv("SERVERSCOM_API_URL", "https://staging")
    plugin.get_option = mock.MagicMock(
        side_effect=lambda k: {"token": "T", "endpoint": None}[k]
    )
    _token, endpoint = plugin._resolve_token_endpoint()
    assert endpoint == "https://staging"


# ------------------------------------------------------------------- #
# _list_for_kind dispatch
# ------------------------------------------------------------------- #


def test_list_kind_baremetal(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter([_make_baremetal()])
    result = list(plugin._list_for_kind(api, "baremetal"))
    api.list_hosts.assert_called_once_with(type="dedicated_server")
    assert len(result) == 1
    assert result[0][1] == "baremetal"


def test_list_kind_sbm(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter([_make_baremetal(type_="sbm_server")])
    result = list(plugin._list_for_kind(api, "sbm"))
    api.list_hosts.assert_called_once_with(type="sbm_server")
    assert result[0][1] == "sbm"


def test_list_kind_k8s(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [_make_baremetal(type_="kubernetes_baremetal_node")]
    )
    result = list(plugin._list_for_kind(api, "k8s_nodes"))
    api.list_hosts.assert_called_once_with(type="kubernetes_baremetal_node")
    assert result[0][1] == "k8s_nodes"


def test_list_kind_cloud(plugin):
    api = mock.MagicMock()
    api.list_instances.return_value = iter([_make_cloud()])
    result = list(plugin._list_for_kind(api, "cloud"))
    api.list_instances.assert_called_once_with()
    assert not api.list_hosts.called
    assert result[0][1] == "cloud"


def test_list_kind_none_two_calls(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [
            _make_baremetal(type_="dedicated_server"),
            _make_baremetal(type_="sbm_server", id_="s1"),
            _make_baremetal(type_="kubernetes_baremetal_node", id_="k1"),
        ]
    )
    api.list_instances.return_value = iter([_make_cloud()])
    result = list(plugin._list_for_kind(api, None))
    api.list_hosts.assert_called_once_with()
    api.list_instances.assert_called_once_with()
    kinds = [k for _server, k in result]
    assert kinds == ["baremetal", "sbm", "k8s_nodes", "cloud"]


def test_list_kind_none_skips_unknown_type(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [_make_baremetal(type_="some_future_type", id_="x1")]
    )
    api.list_instances.return_value = iter([])
    result = list(plugin._list_for_kind(api, None))
    assert result == []


def test_list_kind_invalid_raises(plugin):
    api = mock.MagicMock()
    with pytest.raises(AnsibleParserError, match="Unknown resource kind"):
        list(plugin._list_for_kind(api, "vm"))


# ------------------------------------------------------------------- #
# Helpers
# ------------------------------------------------------------------- #


def test_hostname_baremetal(plugin):
    assert plugin._hostname(_make_baremetal(), "baremetal") == "bm-host-1"


def test_hostname_cloud(plugin):
    assert plugin._hostname(_make_cloud(), "cloud") == "cloud-host-1"


def test_hostname_fallback_to_id(plugin):
    s = _make_baremetal()
    s["title"] = ""
    assert plugin._hostname(s, "baremetal") == "bm1"


def test_region_baremetal(plugin):
    assert plugin._region(_make_baremetal(), "baremetal") == "AMS1"


def test_region_cloud(plugin):
    assert plugin._region(_make_cloud(), "cloud") == "ams1"


# ------------------------------------------------------------------- #
# IP mapping
# ------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "ip_type,expected",
    [
        ("public_ipv4", "1.1.1.1"),
        ("private_ipv4", "10.0.0.1"),
        ("oob_ipv4", "192.168.0.1"),
        ("public_ipv6", None),
        ("local_ipv4", None),
    ],
)
def test_ip_baremetal(plugin, ip_type, expected):
    assert plugin._ip(_make_baremetal(), "baremetal", ip_type) == expected


@pytest.mark.parametrize(
    "ip_type,expected",
    [
        ("public_ipv4", "2.2.2.2"),
        ("private_ipv4", "10.1.0.1"),
        ("public_ipv6", "2001:db8::1"),
        ("local_ipv4", "172.16.0.1"),
        ("oob_ipv4", None),
    ],
)
def test_ip_cloud(plugin, ip_type, expected):
    assert plugin._ip(_make_cloud(), "cloud", ip_type) == expected


def test_ip_oob_only_for_baremetal(plugin):
    sbm = _make_baremetal(type_="sbm_server")
    # sbm/k8s don't expose oob in our mapping
    assert plugin._ip(sbm, "sbm", "oob_ipv4") is None


# ------------------------------------------------------------------- #
# Label match / exclusion
# ------------------------------------------------------------------- #


def test_matches_labels_empty_required(plugin):
    assert plugin._matches_labels({"a": "b"}, {}) is True


def test_matches_labels_all_match(plugin):
    assert plugin._matches_labels({"a": "b", "c": "d"}, {"a": "b"}) is True


def test_matches_labels_value_mismatch(plugin):
    assert plugin._matches_labels({"a": "X"}, {"a": "b"}) is False


def test_matches_labels_missing_key(plugin):
    assert plugin._matches_labels({}, {"a": "b"}) is False


def test_exclude_no_rules(plugin):
    assert (
        plugin._is_excluded(_make_baremetal(), "baremetal", []) is False
    )


def test_exclude_by_region(plugin):
    rules = [{"regions": ["AMS1"]}]
    assert plugin._is_excluded(_make_baremetal(), "baremetal", rules) is True


def test_exclude_by_region_no_match(plugin):
    rules = [{"regions": ["FRA1"]}]
    assert plugin._is_excluded(_make_baremetal(), "baremetal", rules) is False


def test_exclude_by_label(plugin):
    rules = [{"labels": {"env": "prod"}}]
    s = _make_baremetal(labels={"env": "prod"})
    assert plugin._is_excluded(s, "baremetal", rules) is True


def test_exclude_region_and_label_both_required(plugin):
    rules = [{"regions": ["AMS1"], "labels": {"env": "prod"}}]
    s_match = _make_baremetal(labels={"env": "prod"})
    s_region_only = _make_baremetal(labels={"env": "dev"})
    assert plugin._is_excluded(s_match, "baremetal", rules) is True
    assert plugin._is_excluded(s_region_only, "baremetal", rules) is False


def test_exclude_multiple_rules_or(plugin):
    rules = [
        {"regions": ["AMS2"]},
        {"labels": {"decommissioned": "true"}},
    ]
    s1 = _make_baremetal(location_code="AMS2")
    s2 = _make_baremetal(labels={"decommissioned": "true"})
    s3 = _make_baremetal()
    assert plugin._is_excluded(s1, "baremetal", rules) is True
    assert plugin._is_excluded(s2, "baremetal", rules) is True
    assert plugin._is_excluded(s3, "baremetal", rules) is False


# ------------------------------------------------------------------- #
# Group sanitization
# ------------------------------------------------------------------- #


def test_sanitize_group_simple(plugin):
    assert plugin._sanitize_group("AMS1") == "AMS1"


def test_sanitize_group_dashes(plugin):
    assert plugin._sanitize_group("ams-1") == "ams_1"


def test_sanitize_group_dots_and_spaces(plugin):
    assert plugin._sanitize_group("a.b c") == "a_b_c"


# ------------------------------------------------------------------- #
# Grouping behaviour
# ------------------------------------------------------------------- #


def test_add_to_groups_assign(plugin):
    plugin._add_to_groups("h1", _make_baremetal(), "myprod", None)
    plugin.inventory.add_group.assert_called_once_with("myprod")
    plugin.inventory.add_child.assert_called_once_with("myprod", "h1")


def test_add_to_groups_group_by(plugin):
    plugin._add_to_groups("h1", _make_baremetal(), None, "location_code")
    plugin.inventory.add_group.assert_called_once_with("AMS1")
    plugin.inventory.add_child.assert_called_once_with("AMS1", "h1")


def test_add_to_groups_group_by_missing_attr(plugin):
    plugin._add_to_groups("h1", _make_baremetal(), None, "nope")
    assert not plugin.inventory.add_group.called


def test_add_to_groups_both_set_raises(plugin):
    with pytest.raises(AnsibleParserError, match="mutually exclusive"):
        plugin._add_to_groups("h1", _make_baremetal(), "g", "location_code")


def test_add_to_groups_neither_set(plugin):
    plugin._add_to_groups("h1", _make_baremetal(), None, None)
    assert not plugin.inventory.add_group.called


# ------------------------------------------------------------------- #
# Host var assignment
# ------------------------------------------------------------------- #


def test_set_host_vars_baremetal(plugin):
    s = _make_baremetal()
    plugin._set_host_vars("h1", s, "baremetal", "public_ipv4", {})
    calls = {c.args[1]: c.args[2] for c in plugin.inventory.set_variable.mock_calls}
    assert calls["ansible_host"] == "1.1.1.1"
    assert calls["public_ip"] == "1.1.1.1"
    assert calls["private_ip"] == "10.0.0.1"
    assert calls["oob_ip"] == "192.168.0.1"
    assert calls["public_ipv6"] is None  # baremetal
    assert calls["local_ip"] is None
    assert calls["additional_ip_addresses"] == []
    assert calls["sc_kind"] == "baremetal"
    assert calls["title"] == "bm-host-1"
    assert calls["status"] == "active"


def test_set_host_vars_cloud(plugin):
    s = _make_cloud()
    plugin._set_host_vars("h1", s, "cloud", "public_ipv6", {})
    calls = {c.args[1]: c.args[2] for c in plugin.inventory.set_variable.mock_calls}
    assert calls["ansible_host"] == "2001:db8::1"
    assert calls["public_ipv6"] == "2001:db8::1"
    assert calls["local_ip"] == "172.16.0.1"
    assert calls["oob_ip"] is None
    assert calls["sc_kind"] == "cloud"


def test_set_host_vars_missing_ansible_host_ip(plugin):
    s = _make_baremetal(public=None)
    plugin._set_host_vars("h1", s, "baremetal", "public_ipv4", {})
    calls = {c.args[1]: c.args[2] for c in plugin.inventory.set_variable.mock_calls}
    assert "ansible_host" not in calls
    assert calls["public_ip"] is None


def test_set_host_vars_extra_vars_override_raw(plugin):
    s = _make_baremetal()
    plugin._set_host_vars(
        "h1", s, "baremetal", "public_ipv4", {"status": "overridden"}
    )
    # Last write wins; collect ordered (host, key, value) tuples
    assignments = [
        (c.args[1], c.args[2]) for c in plugin.inventory.set_variable.mock_calls
    ]
    # Find every assignment to 'status'; the last one must be from extra_vars
    status_assignments = [v for k, v in assignments if k == "status"]
    assert status_assignments[-1] == "overridden"


# ------------------------------------------------------------------- #
# Full filter pipeline via _apply_resource
# ------------------------------------------------------------------- #


def test_apply_resource_region_filter(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [
            _make_baremetal(id_="a", title="ha", location_code="AMS1"),
            _make_baremetal(id_="b", title="hb", location_code="FRA1"),
        ]
    )
    plugin._apply_resource(
        api, {"kind": "baremetal", "regions": ["AMS1"]}
    )
    added = [c.args[0] for c in plugin.inventory.add_host.mock_calls]
    assert added == ["ha"]


def test_apply_resource_name_regex(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [
            _make_baremetal(id_="a", title="web-1"),
            _make_baremetal(id_="b", title="db-1"),
        ]
    )
    plugin._apply_resource(
        api, {"kind": "baremetal", "name_regex": "^web-"}
    )
    added = [c.args[0] for c in plugin.inventory.add_host.mock_calls]
    assert added == ["web-1"]


def test_apply_resource_labels_and(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [
            _make_baremetal(id_="a", title="ha", labels={"env": "prod"}),
            _make_baremetal(
                id_="b", title="hb", labels={"env": "prod", "tier": "web"}
            ),
            _make_baremetal(id_="c", title="hc", labels={"env": "dev"}),
        ]
    )
    plugin._apply_resource(
        api,
        {"kind": "baremetal", "labels": {"env": "prod", "tier": "web"}},
    )
    added = [c.args[0] for c in plugin.inventory.add_host.mock_calls]
    assert added == ["hb"]


def test_apply_resource_status_filter(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [
            _make_baremetal(id_="a", title="ha", status="active"),
            _make_baremetal(id_="b", title="hb", status="pending"),
        ]
    )
    plugin._apply_resource(
        api, {"kind": "baremetal", "status_filter": ["active"]}
    )
    added = [c.args[0] for c in plugin.inventory.add_host.mock_calls]
    assert added == ["ha"]


def test_apply_resource_exclude(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [
            _make_baremetal(
                id_="a", title="ha", location_code="AMS1",
                labels={"env": "production"},
            ),
            _make_baremetal(
                id_="b", title="hb", location_code="AMS1",
                labels={"env": "dev"},
            ),
        ]
    )
    plugin._apply_resource(
        api,
        {
            "kind": "baremetal",
            "regions": ["AMS1"],
            "exclude": [{"labels": {"env": "production"}}],
        },
    )
    added = [c.args[0] for c in plugin.inventory.add_host.mock_calls]
    assert added == ["hb"]


def test_apply_resource_invalid_ansible_host_raises(plugin):
    api = mock.MagicMock()
    with pytest.raises(AnsibleParserError, match="Invalid ansible_host"):
        plugin._apply_resource(
            api, {"kind": "baremetal", "ansible_host": "bogus"}
        )


def test_apply_resource_group_and_group_by_raises(plugin):
    api = mock.MagicMock()
    api.list_hosts.return_value = iter([])
    with pytest.raises(AnsibleParserError, match="mutually exclusive"):
        plugin._apply_resource(
            api,
            {
                "kind": "baremetal",
                "assign_inventory_group": "g",
                "group_by": "location_code",
            },
        )


# ------------------------------------------------------------------- #
# parse(): resources contract
# ------------------------------------------------------------------- #


def _stub_parse_deps(p, resources):
    """Stub out parse() side-effects so we can drive validation only."""
    p._read_config_data = mock.MagicMock()
    p._resolve_token_endpoint = mock.MagicMock(return_value=("T", "E"))
    p._build_api = mock.MagicMock(return_value=mock.MagicMock())
    p._apply_resource = mock.MagicMock()
    p.get_option = mock.MagicMock(return_value=resources)
    # BaseInventoryPlugin.parse() needs inventory/loader/path; mock them.
    with mock.patch.object(
        InventoryModule.__bases__[0], "parse", return_value=None
    ):
        p.parse(mock.MagicMock(), mock.MagicMock(), "/tmp/foo.sc_api.yml")


def test_parse_no_resources_fetches_all(plugin):
    _stub_parse_deps(plugin, None)
    plugin._apply_resource.assert_called_once_with(mock.ANY, {})


def test_parse_empty_resources_fetches_all(plugin):
    _stub_parse_deps(plugin, [])
    plugin._apply_resource.assert_called_once_with(mock.ANY, {})


def test_parse_block_without_kind_raises(plugin):
    plugin._read_config_data = mock.MagicMock()
    plugin._resolve_token_endpoint = mock.MagicMock(return_value=("T", "E"))
    plugin._build_api = mock.MagicMock(return_value=mock.MagicMock())
    plugin._apply_resource = mock.MagicMock()
    plugin.get_option = mock.MagicMock(return_value=[{}])
    with mock.patch.object(
        InventoryModule.__bases__[0], "parse", return_value=None
    ):
        with pytest.raises(AnsibleParserError, match="must specify `kind`"):
            plugin.parse(
                mock.MagicMock(), mock.MagicMock(), "/tmp/foo.sc_api.yml"
            )


def test_apply_resource_tolerates_unknown_keys(plugin):
    """Plugin code reads documented keys via .get(); unknown keys are no-ops."""
    api = mock.MagicMock()
    api.list_hosts.return_value = iter([_make_baremetal()])
    plugin._apply_resource(
        api,
        {
            "kind": "baremetal",
            "unknown_extra_key": "noise",
            "another_typo": {"nested": "value"},
        },
    )
    assert plugin.inventory.add_host.called


def test_parse_block_with_kind_runs(plugin):
    _stub_parse_deps(plugin, [{"kind": "baremetal"}])
    plugin._apply_resource.assert_called_once_with(
        mock.ANY, {"kind": "baremetal"}
    )
