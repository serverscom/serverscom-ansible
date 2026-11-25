# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import pytest
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    APIError404,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.bgp import (
    ScBgpGroup,
    ScBgpGroupInfo,
    ScBgpGroupsInfo,
    find_bgp_group,
    plan_prefixes,
    resolve_host_ids,
    resolve_location_ids,
)


__metaclass__ = type


def prefix(id, net, mask, status="active", created_at="2025-12-31T00:00:00Z"):
    return {
        "id": id,
        "prefix": f"{net}/{mask}",
        "mask": mask,
        "status": status,
        "created_at": created_at,
    }


def group(status="active", prefixes=None, **kwargs):
    g = {
        "id": "grp1",
        "name": "bgp-1",
        "network_type": "public",
        "asn": 7979,
        "session_type": "ibgp",
        "status": status,
        "location_ids": [1],
        "hosts": [
            {"server_id": "srv1", "location_id": 1},
            {"server_id": "srv2", "location_id": 1},
        ],
        "announced_prefixes": prefixes or [],
        "max_prefix_limit": None,
        "labels": {},
    }
    g.update(kwargs)
    return g


def not_found():
    return APIError404(msg="Not found", api_url="/bgp_groups/x", status_code=404)


def make(checkmode=False, **kwargs):
    params = {
        "endpoint": "https://api.servers.com/v1",
        "token": "test-token",
        "state": "present",
        "bgp_group_id": None,
        "name": "bgp-1",
        "network_type": None,
        "asn": None,
        "location_ids": None,
        "location_codes": None,
        "hosts": None,
        "announced_prefixes": None,
        "prune_prefixes": False,
        "labels": None,
        "wait": 600,
        "update_interval": 5,
        "checkmode": checkmode,
    }
    params.update(kwargs)
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.bgp.ScApi"
    ):
        return ScBgpGroup(**params)


@pytest.fixture(autouse=True)
def no_sleep():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.bgp.time.sleep"
    ):
        yield


# ─── resolvers ───


def test_resolve_location_codes():
    api = mock.MagicMock()
    api.list_locations.return_value = iter(
        [{"id": 1, "code": "AMS1"}, {"id": 2, "code": "DFW1"}]
    )
    assert resolve_location_ids(api, location_codes=["dfw1", "AMS1", "DFW1"]) == [2, 1]


def test_resolve_location_codes_missing():
    api = mock.MagicMock()
    api.list_locations.return_value = iter([{"id": 1, "code": "AMS1"}])
    with pytest.raises(ModuleError) as e:
        resolve_location_ids(api, location_codes=["AMS1", "XXX1"])
    assert "XXX1" in e.value.msg


def test_resolve_location_none():
    assert resolve_location_ids(mock.MagicMock()) is None


def test_resolve_hosts_mixed():
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [{"id": "srv9", "title": "web-01"}, {"id": "srv8", "title": "web-011"}]
    )
    hosts = [{"server_id": "srv1", "hostname": None}, {"server_id": None, "hostname": "web-01"}]
    assert resolve_host_ids(api, hosts) == ["srv1", "srv9"]
    api.list_hosts.assert_called_once_with(search_pattern="web-01")


def test_resolve_hosts_ambiguous():
    api = mock.MagicMock()
    api.list_hosts.return_value = iter(
        [{"id": "srv9", "title": "web-01"}, {"id": "srv8", "title": "web-01"}]
    )
    with pytest.raises(ModuleError) as e:
        resolve_host_ids(api, [{"server_id": None, "hostname": "web-01"}])
    assert "Multiple" in e.value.msg


def test_find_by_name_exact_match():
    api = mock.MagicMock()
    api.list_bgp_groups.return_value = iter(
        [group(id="a", name="bgp-10"), group(id="b", name="bgp-1")]
    )
    assert find_bgp_group(api, name="bgp-1")["id"] == "b"
    api.list_bgp_groups.assert_called_once_with(search_pattern="bgp-1")


def test_find_by_id_not_found():
    api = mock.MagicMock()
    api.get_bgp_group.side_effect = not_found()
    assert find_bgp_group(api, bgp_group_id="x") is None


# ─── plan_prefixes ───


A = prefix("A", "10.0.0.0", 29, created_at="2025-01-01T00:00:00Z")
B = prefix("B", "10.0.1.0", 29, created_at="2025-01-02T00:00:00Z")
C = prefix("C", "10.0.2.0", 28)
R = prefix("R", "10.0.3.0", 29, status="removing")


def ids(prefixes):
    return [p["id"] for p in prefixes]


def test_plan_no_existing():
    plan = plan_prefixes(group(), [{"mask": 29}, {"mask": 28}], prune=False)
    assert plan["add"] == [{"mask": 28}, {"mask": 29}]
    assert plan["keep"] == [] and plan["remove"] == [] and plan["extra"] == []


def test_plan_idempotent_by_mask():
    plan = plan_prefixes(group(prefixes=[A]), [{"mask": 29}], prune=False)
    assert plan["add"] == [] and ids(plan["keep"]) == ["A"]


def test_plan_ignores_removing():
    plan = plan_prefixes(group(prefixes=[R]), [{"mask": 29}], prune=True)
    assert plan["add"] == [{"mask": 29}]
    assert plan["keep"] == [] and plan["remove"] == []


def test_plan_count_match():
    plan = plan_prefixes(
        group(prefixes=[A, B, C]), [{"mask": 29}, {"mask": 28}, {"mask": 28}], False
    )
    assert plan["add"] == [{"mask": 28}]
    assert ids(plan["extra"]) == ["B"]  # newest /29 is the extra one
    assert ids(plan["keep"]) == ["A", "B", "C"]  # kept without prune


def test_plan_prune_unrequested_mask():
    plan = plan_prefixes(group(prefixes=[A, C]), [{"mask": 28}], prune=True)
    assert ids(plan["remove"]) == ["A"]
    assert ids(plan["keep"]) == ["C"]


def test_plan_prune_ambiguous_fails():
    with pytest.raises(ModuleError) as e:
        plan_prefixes(group(prefixes=[A, B]), [{"mask": 29}], prune=True)
    assert "ambiguous" in e.value.msg


def test_plan_prune_with_pin():
    plan = plan_prefixes(
        group(prefixes=[A, B]), [{"prefix": "10.0.1.0/29"}], prune=True
    )
    assert ids(plan["keep"]) == ["B"]
    assert ids(plan["remove"]) == ["A"]


def test_plan_pin_by_id_plus_mask():
    plan = plan_prefixes(group(prefixes=[A]), [{"id": "A"}, {"mask": 29}], False)
    assert ids(plan["keep"]) == ["A"]
    assert plan["add"] == [{"mask": 29}]


def test_plan_unknown_prefix_is_requested():
    plan = plan_prefixes(
        group(prefixes=[A]),
        [{"prefix": "192.0.2.0/24"}, {"prefix": "192.0.2.0/24"}, {"mask": 29}],
        False,
    )
    assert plan["add"] == [{"prefix": "192.0.2.0/24"}]
    assert ids(plan["keep"]) == ["A"]


def test_plan_requested_prefix_idempotent():
    existing = prefix("P", "192.0.2.0", 24)
    plan = plan_prefixes(group(prefixes=[existing]), [{"prefix": "192.0.2.0/24"}], True)
    assert plan["add"] == [] and plan["remove"] == []


def test_plan_prefix_host_bits():
    with pytest.raises(ModuleError) as e:
        plan_prefixes(group(), [{"prefix": "192.0.2.5/24"}], False)
    assert "Invalid prefix" in e.value.msg


def test_plan_id_not_found():
    with pytest.raises(ModuleError) as e:
        plan_prefixes(group(prefixes=[A]), [{"id": "nope"}], False)
    assert "not found" in e.value.msg


def test_plan_invalid_prefix():
    with pytest.raises(ModuleError) as e:
        plan_prefixes(group(prefixes=[A]), [{"prefix": "garbage"}], False)
    assert "Invalid prefix" in e.value.msg


# ─── create ───


def test_create():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}],
             announced_prefixes=[{"mask": 29, "prefix": None, "id": None}])
    m.api.list_bgp_groups.return_value = iter([])
    m.api.post_bgp_group.return_value = group(status="pending")
    m.api.get_bgp_group.return_value = group(prefixes=[A])
    result = m.run()
    assert result["changed"] is True
    assert result["bgp_group"]["status"] == "active"
    assert result["prefixes_added"] == [{"mask": 29}]
    m.api.post_bgp_group.assert_called_once_with(
        name="bgp-1",
        network_type="public",
        location_ids=[1],
        hosts=[{"server_id": "srv1"}],
        asn=None,
        announced_prefixes=[{"mask": 29}],
        labels=None,
    )


def test_create_waits_for_pending_prefixes():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}])
    m.api.list_bgp_groups.return_value = iter([])
    m.api.post_bgp_group.return_value = group(status="pending")
    pending = prefix("A", "10.0.0.0", 29, status="pending")
    m.api.get_bgp_group.side_effect = [
        group(status="pending"),
        group(prefixes=[pending]),
        group(prefixes=[A]),
    ]
    result = m.run()
    assert result["bgp_group"]["announced_prefixes"][0]["status"] == "active"
    assert m.api.get_bgp_group.call_count == 3


def test_create_failed_prefix():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}])
    m.api.list_bgp_groups.return_value = iter([])
    m.api.post_bgp_group.return_value = group(status="pending")
    m.api.get_bgp_group.return_value = group(
        prefixes=[prefix("A", "10.0.0.0", 29, status="failed")]
    )
    with pytest.raises(ModuleError) as e:
        m.run()
    assert "failed" in e.value.msg


def test_create_failed_group():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}])
    m.api.list_bgp_groups.return_value = iter([])
    m.api.post_bgp_group.return_value = group(status="pending")
    m.api.get_bgp_group.return_value = group(status="failed")
    with pytest.raises(ModuleError):
        m.run()


def test_create_no_wait():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}], wait=0)
    m.api.list_bgp_groups.return_value = iter([])
    m.api.post_bgp_group.return_value = group(status="pending")
    result = m.run()
    assert result["bgp_group"]["status"] == "pending"
    m.api.get_bgp_group.assert_not_called()


def test_create_timeout():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}],
             wait=10, update_interval=5)
    m.api.list_bgp_groups.return_value = iter([])
    m.api.post_bgp_group.return_value = group(status="pending")
    m.api.get_bgp_group.return_value = group(status="pending")
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.bgp.time.time",
        side_effect=[0, 0, 6, 12],
    ):
        with pytest.raises(WaitError):
            m.run()


def test_create_requires_hosts_and_locations():
    m = make(location_ids=[1])
    m.api.list_bgp_groups.return_value = iter([])
    with pytest.raises(ModuleError) as e:
        m.run()
    assert "hosts" in e.value.msg


def test_create_rejects_id():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}],
             announced_prefixes=[{"mask": None, "prefix": None, "id": "A"}])
    m.api.list_bgp_groups.return_value = iter([])
    with pytest.raises(ModuleError):
        m.run()
    m.api.post_bgp_group.assert_not_called()


def test_create_with_prefix():
    m = make(location_ids=[1], hosts=[{"server_id": "srv1", "hostname": None}],
             announced_prefixes=[{"mask": None, "prefix": "192.0.2.0/24", "id": None},
                                 {"mask": 29, "prefix": None, "id": None}],
             wait=0)
    m.api.list_bgp_groups.return_value = iter([])
    m.api.post_bgp_group.return_value = group(status="pending")
    result = m.run()
    assert result["prefixes_added"] == [{"prefix": "192.0.2.0/24"}, {"mask": 29}]
    assert m.api.post_bgp_group.call_args.kwargs["announced_prefixes"] == [
        {"prefix": "192.0.2.0/24"},
        {"mask": 29},
    ]


def test_update_requests_prefix():
    m = make(announced_prefixes=[{"mask": None, "prefix": "10.0.0.0/29", "id": None},
                                 {"mask": None, "prefix": "192.0.2.0/24", "id": None}],
             wait=0)
    m.api.list_bgp_groups.return_value = iter([group(prefixes=[A])])
    m.api.put_bgp_group.return_value = group(status="pending")
    m.run()
    m.api.put_bgp_group.assert_called_once_with(
        "grp1", {"announced_prefixes": [{"id": "A"}, {"prefix": "192.0.2.0/24"}]}
    )


def test_create_checkmode():
    m = make(checkmode=True, asn=64512, location_ids=[1],
             hosts=[{"server_id": "srv1", "hostname": None}])
    m.api.list_bgp_groups.return_value = iter([])
    result = m.run()
    assert result["changed"] is True
    assert result["bgp_group"]["session_type"] == "ebgp"
    m.api.post_bgp_group.assert_not_called()


def test_create_by_id_not_found():
    m = make(bgp_group_id="nope")
    m.api.get_bgp_group.side_effect = not_found()
    with pytest.raises(ModuleError) as e:
        m.run()
    assert "not found" in e.value.msg


# ─── update ───


def test_no_changes():
    m = make(location_ids=[1], hosts=[{"server_id": "srv2", "hostname": None},
                                      {"server_id": "srv1", "hostname": None}],
             labels={}, announced_prefixes=[{"mask": 29, "prefix": None, "id": None}])
    m.api.list_bgp_groups.return_value = iter([group(prefixes=[A])])
    result = m.run()
    assert result["changed"] is False
    m.api.put_bgp_group.assert_not_called()


def test_no_changes_on_pending_group():
    m = make(wait=0, labels={})
    m.api.list_bgp_groups.return_value = iter([group(status="pending")])
    result = m.run()
    assert result["changed"] is False


def test_update_hosts_and_labels():
    m = make(hosts=[{"server_id": "srv1", "hostname": None},
                    {"server_id": "srv3", "hostname": None}],
             labels={"env": "prod"})
    m.api.list_bgp_groups.return_value = iter([group()])
    m.api.put_bgp_group.return_value = group(status="pending")
    m.api.get_bgp_group.return_value = group()
    result = m.run()
    assert result["changed"] is True
    m.api.put_bgp_group.assert_called_once_with(
        "grp1",
        {
            "labels": {"env": "prod"},
            "hosts": [{"server_id": "srv1"}, {"server_id": "srv3"}],
        },
    )


def test_update_name_by_id():
    m = make(bgp_group_id="grp1", name="renamed")
    m.api.get_bgp_group.return_value = group()
    m.api.put_bgp_group.return_value = group(name="renamed")
    m.run()
    m.api.put_bgp_group.assert_called_once_with("grp1", {"name": "renamed"})


def test_update_adds_prefix_full_list():
    m = make(announced_prefixes=[{"mask": 29, "prefix": None, "id": None},
                                 {"mask": 29, "prefix": None, "id": None}])
    m.api.list_bgp_groups.return_value = iter([group(prefixes=[A, R])])
    m.api.put_bgp_group.return_value = group(status="pending")
    m.api.get_bgp_group.return_value = group(prefixes=[A, B])
    result = m.run()
    m.api.put_bgp_group.assert_called_once_with(
        "grp1", {"announced_prefixes": [{"id": "A"}, {"mask": 29}]}
    )
    assert result["prefixes_added"] == [{"mask": 29}]


def test_update_extra_prefix_warns_without_prune():
    m = make(announced_prefixes=[{"mask": 29, "prefix": None, "id": None}])
    m.api.list_bgp_groups.return_value = iter([group(prefixes=[A, C])])
    result = m.run()
    assert result["changed"] is False
    assert "10.0.2.0/28" in result["warnings"][0]
    m.api.put_bgp_group.assert_not_called()


def test_update_prune():
    m = make(announced_prefixes=[{"mask": 29, "prefix": None, "id": None}],
             prune_prefixes=True)
    m.api.list_bgp_groups.return_value = iter([group(prefixes=[A, C])])
    m.api.put_bgp_group.return_value = group(status="pending")
    m.api.get_bgp_group.return_value = group(prefixes=[A])
    result = m.run()
    m.api.put_bgp_group.assert_called_once_with(
        "grp1", {"announced_prefixes": [{"id": "A"}]}
    )
    assert ids(result["prefixes_removed"]) == ["C"]


def test_update_pending_waits_then_updates():
    m = make(labels={"env": "prod"})
    m.api.list_bgp_groups.return_value = iter([group(status="pending")])
    m.api.get_bgp_group.side_effect = [
        group(status="pending"),
        group(),  # active, ensure_active done
        group(labels={"env": "prod"}),  # after put
    ]
    m.api.put_bgp_group.return_value = group(labels={"env": "prod"})
    result = m.run()
    assert result["changed"] is True
    m.api.put_bgp_group.assert_called_once()


def test_update_pending_no_wait_fails():
    m = make(labels={"env": "prod"}, wait=0)
    m.api.list_bgp_groups.return_value = iter([group(status="pending")])
    with pytest.raises(ModuleError) as e:
        m.run()
    assert "pending" in e.value.msg
    m.api.put_bgp_group.assert_not_called()


@pytest.mark.parametrize("status", ["failed", "removing"])
def test_update_not_updatable_status(status):
    m = make(labels={"env": "prod"})
    m.api.list_bgp_groups.return_value = iter([group(status=status)])
    with pytest.raises(ModuleError) as e:
        m.run()
    assert status in e.value.msg
    m.api.put_bgp_group.assert_not_called()


def test_update_checkmode_pending_does_not_wait():
    m = make(checkmode=True, labels={"env": "prod"})
    m.api.list_bgp_groups.return_value = iter([group(status="pending")])
    result = m.run()
    assert result["changed"] is True
    assert result["bgp_group"]["labels"] == {"env": "prod"}
    m.api.get_bgp_group.assert_not_called()
    m.api.put_bgp_group.assert_not_called()


def test_asn_on_ibgp_group_fails():
    m = make(asn=64512)
    m.api.list_bgp_groups.return_value = iter([group()])
    with pytest.raises(ModuleError) as e:
        m.run()
    assert "iBGP" in e.value.msg


def test_asn_change_fails():
    m = make(asn=64513)
    m.api.list_bgp_groups.return_value = iter(
        [group(asn=64512, session_type="ebgp")]
    )
    with pytest.raises(ModuleError):
        m.run()


def test_asn_same_ok():
    m = make(asn=64512)
    m.api.list_bgp_groups.return_value = iter(
        [group(asn=64512, session_type="ebgp")]
    )
    assert m.run()["changed"] is False


def test_update_interval_longer_than_wait():
    with pytest.raises(ModuleError):
        make(wait=3, update_interval=5)


# ─── absent ───


def test_absent_not_found():
    m = make(state="absent")
    m.api.list_bgp_groups.return_value = iter([])
    assert m.run() == {"changed": False, "bgp_group": {}}


def test_absent_deletes_and_waits():
    m = make(state="absent")
    m.api.list_bgp_groups.return_value = iter([group()])
    m.api.get_bgp_group.side_effect = [group(status="removing"), not_found()]
    assert m.run()["changed"] is True
    m.api.delete_bgp_group.assert_called_once_with("grp1")


def test_absent_pending_waits_for_active():
    m = make(state="absent", wait=0)
    m.api.list_bgp_groups.return_value = iter([group(status="pending")])
    with pytest.raises(ModuleError):
        m.run()
    m.api.delete_bgp_group.assert_not_called()


def test_absent_already_removing():
    m = make(state="absent")
    m.api.list_bgp_groups.return_value = iter([group(status="removing")])
    m.api.get_bgp_group.side_effect = [not_found()]
    assert m.run()["changed"] is False
    m.api.delete_bgp_group.assert_not_called()


def test_absent_checkmode():
    m = make(state="absent", checkmode=True)
    m.api.list_bgp_groups.return_value = iter([group()])
    assert m.run()["changed"] is True
    m.api.delete_bgp_group.assert_not_called()


# ─── info ───


def test_group_info_not_found():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.bgp.ScApi"
    ):
        info = ScBgpGroupInfo("e", "t", name="nope")
    info.api.list_bgp_groups.return_value = iter([])
    with pytest.raises(ModuleError):
        info.run()


def test_groups_info_resolves_filters():
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.bgp.ScApi"
    ):
        info = ScBgpGroupsInfo("e", "t", location_code="ams1", hostname="web-01")
    info.api.list_locations.return_value = iter([{"id": 1, "code": "AMS1"}])
    info.api.list_hosts.return_value = iter([{"id": "srv1", "title": "web-01"}])
    info.api.list_bgp_groups.return_value = iter([group()])
    result = info.run()
    assert result["bgp_groups"][0]["id"] == "grp1"
    info.api.list_bgp_groups.assert_called_once_with(
        search_pattern=None,
        status=None,
        location_id=1,
        asn=None,
        server_id="srv1",
        label_selector=None,
    )
