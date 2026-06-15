# Copyright (c) 2020 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import pytest
import mock
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.l2_segment import (
    ScL2Segment,
    _find_l2_segment_id,
)  # noqa


__metaclass__ = type


def test__listdict_to_set_trivial():
    assert ScL2Segment._listdict_to_set([]) == set()


def test__listdict_to_set_None():
    assert ScL2Segment._listdict_to_set(None) == set()


def test__set_to_listdict_trivial():
    assert ScL2Segment._set_to_listdict(set()) == []


def test_set_to_listdict_and_listdict_to_set():
    DATA1 = {"id": "foo", "mode": "native"}
    DATA2 = {"id": "bar", "mode": "trunk"}
    DATA = [DATA1, DATA2]
    res = ScL2Segment._set_to_listdict(ScL2Segment._listdict_to_set(DATA))
    assert DATA1 in res
    assert DATA2 in res


def test_prep_absent_list():
    members = [{"id": "GdbY8LmA", "mode": None}]
    old_members = [
        {"id": "3dw6qlmE", "mode": "native"},
        {"id": "LmK5671k", "mode": "native"},
        {"id": "GdbY8LmA", "mode": "native"},
    ]
    res = list(ScL2Segment.prep_absent_list(members, old_members))
    assert res == [
        {
            "id": "GdbY8LmA",
            "mode": "native",
        }
    ]


def test_simplify_members():
    data = [
        {
            "id": "GdbY8LmA",
            "mode": "native",
        }
    ]
    assert list(ScL2Segment._simplify_members(data)) == data


def test_find_l2_segment_id_matches_type():
    api = mock.MagicMock()
    api.list_l2_segments.return_value = [
        {"id": "l2-1", "name": "shared", "type": "sbm"},
        {"id": "l2-2", "name": "shared", "type": "dedicated"},
    ]

    assert _find_l2_segment_id(api, name="shared", type="dedicated") == "l2-2"


def test_find_l2_segment_id_raises_when_required_segment_missing():
    api = mock.MagicMock()
    api.list_l2_segments.return_value = []

    with pytest.raises(ModuleError) as exc_info:
        _find_l2_segment_id(api, name="missing", must=True)

    assert "Segment missing is not found" in exc_info.value.msg


def test_find_l2_segment_id_raises_on_duplicate_name():
    api = mock.MagicMock()
    api.list_l2_segments.return_value = [
        {"id": "l2-1", "name": "shared", "type": "sbm"},
        {"id": "l2-2", "name": "shared", "type": "sbm"},
    ]

    with pytest.raises(ModuleError) as exc_info:
        _find_l2_segment_id(api, name="shared")

    assert "Duplicate segment with name shared found" in exc_info.value.msg
