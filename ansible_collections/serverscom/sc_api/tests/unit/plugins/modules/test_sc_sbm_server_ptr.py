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
    ScSbmServerPtr,
)  # noqa


__metaclass__ = type


PTR_RECORD_1 = {
    "id": "ptr-1",
    "ip": "203.0.113.1",
    "domain": "server1.example.com",
    "ttl": 60,
    "priority": 0,
}

PTR_RECORD_2 = {
    "id": "ptr-2",
    "ip": "203.0.113.2",
    "domain": "server2.example.com",
    "ttl": 300,
    "priority": 10,
}

PTR_RECORD_3 = {
    "id": "ptr-3",
    "ip": "198.51.100.1",
    "domain": "other.example.org",
    "ttl": 60,
    "priority": 0,
}

PTR_RECORDS = [PTR_RECORD_1, PTR_RECORD_2, PTR_RECORD_3]


def create_ptr_instance(
    state="query", ip=None, domain=None, ttl=None, priority=None, checkmode=False
):
    """Create a ScSbmServerPtr instance with mocked API."""
    with mock.patch(
        "ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm.ScApi"
    ):
        return ScSbmServerPtr(
            endpoint="https://api.servers.com/v1",
            token="test-token",
            state=state,
            server_id="test-server",
            ip=ip,
            domain=domain,
            ttl=ttl,
            priority=priority,
            checkmode=checkmode,
        )


def test_find_ptr_empty_list():
    ptr = create_ptr_instance()
    result = list(ptr.find_ptr([], "example.com", "203.0.113.1"))
    assert result == []


def test_find_ptr_by_domain():
    ptr = create_ptr_instance()
    result = list(ptr.find_ptr(PTR_RECORDS, "server1.example.com", None))
    assert result == [PTR_RECORD_1]


def test_find_ptr_by_ip():
    ptr = create_ptr_instance()
    result = list(ptr.find_ptr(PTR_RECORDS, None, "203.0.113.2"))
    assert result == [PTR_RECORD_2]


def test_find_ptr_by_domain_and_ip():
    ptr = create_ptr_instance()
    result = list(ptr.find_ptr(PTR_RECORDS, "server1.example.com", "203.0.113.1"))
    assert result == [PTR_RECORD_1]


def test_find_ptr_no_match():
    ptr = create_ptr_instance()
    result = list(ptr.find_ptr(PTR_RECORDS, "nonexistent.example.com", None))
    assert result == []


def test_find_ptr_no_match_ip():
    ptr = create_ptr_instance()
    result = list(ptr.find_ptr(PTR_RECORDS, None, "10.0.0.1"))
    assert result == []


def test_find_ptr_multiple_matches_by_domain():
    # Test when multiple records could match (though in practice domains are unique)
    records = [
        {"id": "1", "ip": "1.1.1.1", "domain": "test.com"},
        {"id": "2", "ip": "2.2.2.2", "domain": "test.com"},
    ]
    ptr = create_ptr_instance()
    result = list(ptr.find_ptr(records, "test.com", None))
    assert len(result) == 2


def test_find_ptr_both_must_match():
    # When both domain and ip are specified, both must match (AND logic)
    ptr = create_ptr_instance()
    # IP matches PTR_RECORD_1 but domain does not — should NOT match
    result = list(ptr.find_ptr(PTR_RECORDS, "wrong.domain.com", "203.0.113.1"))
    assert result == []
    # Both match PTR_RECORD_1 — should match
    result = list(ptr.find_ptr(PTR_RECORDS, "server1.example.com", "203.0.113.1"))
    assert result == [PTR_RECORD_1]


def test_find_ptr_none_params():
    ptr = create_ptr_instance()
    # Both None means no matching criteria
    result = list(ptr.find_ptr(PTR_RECORDS, None, None))
    assert result == []


# --- run() method tests ---


def test_run_query():
    ptr = create_ptr_instance(state="query")
    ptr.api.list_sbm_server_ptr_records.return_value = iter(PTR_RECORDS)

    result = ptr.run()

    assert result["changed"] is False
    assert result["ptr_records"] == PTR_RECORDS


def test_run_present_new_record():
    ptr = create_ptr_instance(
        state="present", ip="10.0.0.1", domain="new.example.com", ttl=120, priority=5
    )
    ptr.api.list_sbm_server_ptr_records.side_effect = [
        iter([]),  # initial check: no existing records
        iter([{"id": "ptr-new", "ip": "10.0.0.1", "domain": "new.example.com"}]),
    ]

    result = ptr.run()

    assert result["changed"] is True
    ptr.api.post_sbm_server_ptr_record.assert_called_once_with(
        server_id="test-server",
        ip="10.0.0.1",
        domain="new.example.com",
        ttl=120,
        priority=5,
    )


def test_run_present_already_exists():
    ptr = create_ptr_instance(
        state="present", ip="203.0.113.1", domain="server1.example.com"
    )
    ptr.api.list_sbm_server_ptr_records.return_value = iter(PTR_RECORDS)

    result = ptr.run()

    assert result["changed"] is False
    ptr.api.post_sbm_server_ptr_record.assert_not_called()


def test_run_present_checkmode():
    ptr = create_ptr_instance(
        state="present", ip="10.0.0.1", domain="new.example.com", checkmode=True
    )
    ptr.api.list_sbm_server_ptr_records.return_value = iter([])

    result = ptr.run()

    assert result["changed"] is True
    ptr.api.post_sbm_server_ptr_record.assert_not_called()


def test_run_absent_record_found():
    ptr = create_ptr_instance(state="absent", domain="server1.example.com")
    ptr.api.list_sbm_server_ptr_records.side_effect = [
        iter(PTR_RECORDS),  # initial check
        iter([PTR_RECORD_2, PTR_RECORD_3]),  # after deletion
    ]

    result = ptr.run()

    assert result["changed"] is True
    ptr.api.delete_sbm_server_ptr_record.assert_called_once_with(
        server_id="test-server", record_id="ptr-1"
    )


def test_run_absent_not_found():
    ptr = create_ptr_instance(state="absent", domain="nonexistent.example.com")
    ptr.api.list_sbm_server_ptr_records.return_value = iter(PTR_RECORDS)

    result = ptr.run()

    assert result["changed"] is False
    ptr.api.delete_sbm_server_ptr_record.assert_not_called()


def test_run_absent_checkmode():
    ptr = create_ptr_instance(
        state="absent", domain="server1.example.com", checkmode=True
    )
    ptr.api.list_sbm_server_ptr_records.return_value = iter(PTR_RECORDS)

    result = ptr.run()

    assert result["changed"] is True
    ptr.api.delete_sbm_server_ptr_record.assert_not_called()


def test_run_unknown_state():
    ptr = create_ptr_instance(state="invalid")
    ptr.api.list_sbm_server_ptr_records.return_value = iter([])

    with pytest.raises(ModuleError) as exc_info:
        ptr.run()

    assert "Unknown state" in str(exc_info.value.msg)
