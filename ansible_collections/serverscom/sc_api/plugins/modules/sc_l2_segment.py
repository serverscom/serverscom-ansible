#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2020, Servers.com
# GNU General Public License v3.0
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: sc_l2_segment
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Managing L2 segement
description: >
    Create/update/delete L2 segment and it's members.
    This module will fail if two or more existing L2 segments
    has the same name.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    name:
      type: str
      description:
        - Name of the segment
        - This module required to all segments to have unique names
        - If two segments have the same name (even in different location groups
          or having different type), this module fails.
        - Either I(name) or I(segment_id) is required for delete/update of
          existing segment.
        - I(name) is required if new segment need to be created

    segment_id:
      type: str
      description:
        - ID of the segment
        - Can be used for delete or update operations istead if I(name)

    state:
      type: str
      choices: ['absent', 'present']
      default: present
      description:
        - State of the segment
        - C(absent) make sure that segment was deleted
        - If C(absent), and I(type) is specified, delete
          segment of only given type.
        - If C(absent) and I(type) is not specified
          delete segment of any type.

    type:
      type: str
      choices: ['public', 'private']
      description:
        - Type of segment
        - Required if I(state)=C(present)
        - Global Private Network is C(private)
        - Internet is C(public)s
        - If I(type) for existing segment is different, module fails.

    members:
      type: list
      elements: dict
      description:
        - List of servers and mode of connection (native or trunk)
        - (Either I(members) or I(members_present) or I(members_absent)
          required if I(state)=C(present)
        - L2 segment should contains at least one member
        - Server can be member of only one L2 segment in I(mode)=C(native)
        - Server can participate in multiple L2 segments in I(mode)=C(trunk)
        - Server can be present in a given segment only once (e.g. it's impossible
          to have the same segment with two different vlan IDs on the same server)
        - L2 segment is reconfigured to keep only listed members
        - Either I(members) or I(members_present) can be used
        - Either I(members) or I(members_absent) can be used

      suboptions:
        id:
          type: str
          required: true
          description:
            - ID of the server to be present in L2 segment

        mode:
          type: str
          choices: ['trunk', 'native']
          default: native
          description:
            - Access mode of server in L2 segment
            - C(native) provdes direct connection to L2 segment
            - C(trunk) add L2 segment as tagged vlan
            - Server can be only in one segment in C(native) mode
            - Server can be present in multiple L2 segments
              in C(trunk) mode
            - If I(type) is changed for a given server
              it will be reconfigured twice, removed from L2
              segment and added back with a new mode.

    members_present:
      type: list
      elements: dict
      description:
        - List of servers and mode of connection (native or trunk)
        - Existing servers in L2 segement are not affected, except for
          possible mode change (this option only assure that servers are added)
        - (Either I(members) or I(members_present) or I(members_absent)
          required if I(state)=C(present)
        - L2 segment should contains at least one member
        - Server can be member of only one L2 segment in I(mode)=C(native)
        - Server can participate in multiple L2 segments in I(mode)=C(trunk)
        - Server can be present in a given segment only once (e.g. it's impossible
          to have the same segment with two different vlan IDs on the same server).
        - Either I(members) or I(members_present) can be used.
        - Either I(members) or I(members_absent) can be used.

      suboptions:
        id:
          type: str
          required: true
          description:
            - ID of the server to be present in L2 segment

        mode:
          type: str
          choices: ['trunk', 'native']
          default: native
          description:
            - Access mode of server in L2 segment
            - C(native) provdes direct connection to L2 segment
            - C(trunk) add L2 segment as tagged vlan
            - Server can be only in one segment in C(native) mode
            - Server can be present in multiple L2 segments
              in C(trunk) mode
            - If I(type) is changed for a given server
              it will be reconfigured twice, removed from L2
              segment and added back with a new mode.

    members_absent:
      type: list
      elements: dict
      description:
        - List of servers to be absent in L2 segment
        - Other servers in L2 segement are not affected
          (this option only assure that listed servers are removed)
        - (Either I(members) or I(members_present) or I(members_absent)
          required if I(state)=C(present)
        - L2 segment should contains at least two members
        - Either I(members) or I(members_present) can be used.
        - Either I(members) or I(members_absent) can be used.

      suboptions:
        id:
          type: str
          required: true
          description:
            - ID of the server to be present in L2 segment

        mode:
          type: str
          required: false
          description:
            - Ignored, existing for compatibility of
              arguments with I(members_present)

    location_group_id:
        type: str
        description:
          - ID of location group to create L2 segment
          - Used only for I(state)=C(absent) or I(State)=C(present)
          - If members are in different location group than
            specified, module fails.

    labels:
        type: dict
        description:
          - Labels to attach to the instance. If labels do not exist they will be created.
          - Key-value pairs.
          - More info at https://developers.servers.com/api-documentation/v1/#section/Labels.

    wait:
      type: int
      default: 1800
      description:
        - Max wait time for operation to be finished.
        - By default waiting for L2 segment to become active.
        - C(0) disable waiting (fire-and-forget mode)

    update_interval:
      type: int
      default: 30
      description:
        - Interval for polling for of L2 segment
        - Each update consumes API quota.
        - Ignored if I(wait)=C(0)
"""

RETURN = """
l2_segment:
    description:
        - Information about L2 segments
    returned: on success
    type: complex
    contains:
        id:
            type: str
            description:
                - ID of the L2 segement
        name:
            type: str
            description:
                - Name of the L2 segement

        type:
            type: str
            description:
                - Type of the segement. Either C(public) or C(private)
        status:
            type: str
            description:
                - Status of the segment. C(active) means segment is ready
                  to be used.

        location_group_id:
            type: int
            description:
                - Id of the location group where L2 segment was created

        location_group_code:
            type: str
            description:
                - Textual name of the location group

        updated_at:
            type: str
            description:
                - Last update date and time

        created_at:
            type: str
            description:
                - Creation date and time
        networks:
            type: list
            description:
                - List of additional aliases for a given L2 segement
        members:
            type: list
            description:
                - List of L2 segment members (servers)
                - Contains info on mode (C(trunk)/C(native))
                - Contains info on used vlan id (if used)
                - Contains info about current state (C(new)/C(removed)/C(active))

api_url:
    description: URL for the failed request
    returned: on failure
    type: str

status_code:
    description: Status code for the request
    returned: always
    type: int
"""

EXAMPLES = """
- name: Create L2 segment for three servers
  serverscom.sc_api.sc_l2_segment:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    name: L2 example
    type: private
    members:
        - id: 0m592Zmn
          mode: native
        - id: GmyAZkm0
          mode: native
        - id: 7p6bE0p3
          mode: native

- name: Reduce L2 segment to two servers
  serverscom.sc_api.sc_l2_segment:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    name: L2 example
    type: private
    members:
        - id: 0m592Zmn
          mode: native
        - id: GmyAZkm0
          mode: native

- name: Assure server 7p6bE0p3 is present in L2 segment, ignoring other servers
  serverscom.sc_api.sc_l2_segment:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    name: L2 example
    type: private
    members_present:
        - id: 7p6bE0p3
          mode: trunk

- name: Removing 7p6bE0p3 from L2 segment, ignoring other servers
  serverscom.sc_api.sc_l2_segment:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    name: L2 example
    type: private
    members_absent:
        - id: 7p6bE0p3
          mode: trunk

- name: Remove L2 segment
  serverscom.sc_api.sc_l2_segment:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    name: 'L2 example'
    state: absent

- name: Create public L2 segment with specific location_group_id
  serverscom.sc_api.sc_l2_segment:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    name: 'L2 example'
    type: public
    state: present
    location_group_id: 42
    members:
        - id: 0m592Zmn
          mode: native
        - id: GmyAZkm0
          mode: native

- name: Remove L2 segment by id
  serverscom.sc_api.sc_l2_segment:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    segment_id: z3452m0
    state: absent
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_l2_segment import (
    ScL2Segment,
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "name": {},
            "segment_id": {},
            "state": {"choices": ["present", "absent"], "default": "present"},
            "type": {"choices": ["public", "private"]},
            "members": {
                "type": "list",
                "elements": "dict",
                "options": {
                    "id": {"required": True},
                    "mode": {"choices": ["native", "trunk"], "default": "native"},
                },
            },
            "members_present": {
                "type": "list",
                "elements": "dict",
                "options": {
                    "id": {"required": True},
                    "mode": {"choices": ["native", "trunk"], "default": "native"},
                },
            },
            "members_absent": {
                "type": "list",
                "elements": "dict",
                "options": {
                    "id": {"required": True},
                    "mode": {},
                },
            },
            "location_group_id": {},
            "labels": {"type": "dict"},
            "wait": {"type": "int", "default": 1800},
            "update_interval": {"type": "int", "default": 30},
        },
        mutually_exclusive=[
            ("name", "segment_id"),
            ("members", "members_present"),
            ("members", "members_absent"),
        ],
        supports_check_mode=True,
    )
    if module.params["state"] == "present":
        if not any(
            [
                module.params["members"],
                module.params["members_present"],
                module.params["members_absent"],
            ]
        ):
            module.fail_json(
                "state=present required either members, or members_present, or members_absent"
            )
    try:
        sc_info = ScL2Segment(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            name=module.params["name"],
            segment_id=module.params["segment_id"],
            state=module.params["state"],
            type=module.params["type"],
            members=module.params["members"],
            members_present=module.params["members_present"],
            members_absent=module.params["members_absent"],
            location_group_id=module.params["location_group_id"],
            labels=module.params.get("labels"),
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
        module.exit_json(**sc_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
