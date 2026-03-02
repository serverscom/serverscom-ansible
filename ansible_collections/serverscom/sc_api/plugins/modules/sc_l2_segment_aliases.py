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
module: sc_l2_segment_aliases
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Managing L2 segement
description: >
    Create/delete L2 segment aliases.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    name:
      type: str
      description:
        - Name of the segment
        - This module required to all segments to have unique names
        - If two segments have the same name (even in different location groups
          or having different type), this module fails
        - Either I(name) or I(segment_id) is required for delete/update of
          existing segment.
        - I(name) is required if new segment need to be created

    segment_id:
      type: str
      description:
        - ID of the segment
        - Either I(name) or I(segment_id) can be used

    count:
      type: int
      description:
        - Number of aliases assigned to L2 segment
        - Either I(count) or I(aliases_absent) can be used
        - Either I(count) or I(aliases_absent) must be specified
        - Value 0 removes all aliases

    aliases_absent:
      type: list
      elements: str
      description:
        - List of aliases (by IP or ID) to be absent for the segment
        - Either I(count) or I(aliases_absent) can be used
        - Either I(count) or I(aliases_absent) must be specified

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
id:
    description:
        - Id of the segment
    returned: on success
    type: list

aliases:
    description:
        - List of aliases
    returned: on success
    type: complex
    contains:
      id:
        description:
          - ID of alias
        type: str
      family:
        type: str
        description:
          - Either ipv4 or ipv6
      cidr:
        type: str
        description:
          - IP address of the alias with /32 mask

alias_count:
    description:
        - Number of aliases
    returned: on success
    type: int

ipv4_list:
    description:
        - List of IPv4 addresses
    returned: on success
    type: list
    elements: str

ipv6_list:
    description:
        - List of IPv6 addresses
    returned: on success
    type: list
    elements: str

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
- name: Assign two aliases to a segment
  serverscom.sc_api.sc_l2_segment_aliases:
    token: '{{ lookup("env", "SC_TOKEN") }}'
    name: L2 example
    count: 2
  register: l2

- name: Report aliases
  debug: var=l2.l2_segment.networks

- name: Remove aliases from a segment by ID
  serverscom.sc_api.sc_l2_segment:
    token: '{{ lookup("env", "SC_TOKEN") }}'
    segment_id: 0m592Zmn
    aliases_absent:
      - 7p6bE0p3

- name: Remove aliases from a segment by value
  serverscom.sc_api.sc_l2_segment:
    token: '{{ lookup("env", "SC_TOKEN") }}'
    segment_id: L2 example
    aliases_absent:
      - 203.0.113.41
      - 203.0.113.42

- name: Remove all aliases from a segment
  serverscom.sc_api.sc_l2_segment:
    token: '{{ lookup("env", "SC_TOKEN") }}'
    segment_id: L2 example
    count: 0
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_l2_segment import (
    ScL2SegmentAliases,
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "name": {},
            "segment_id": {},
            "count": {"type": "int"},
            "aliases_absent": {
                "type": "list",
                "elements": "str",
            },
            "wait": {"type": "int", "default": 1800},
            "update_interval": {"type": "int", "default": 30},
        },
        mutually_exclusive=[
            ("name", "segment_id"),
            ("count", "aliases_absent"),
        ],
        required_one_of=[
            ("name", "segment_id"),
            ("count", "aliases_absent"),
        ],
        supports_check_mode=True,
    )
    try:
        sc_info = ScL2SegmentAliases(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            name=module.params["name"],
            segment_id=module.params["segment_id"],
            count=module.params["count"],
            aliases_absent=module.params["aliases_absent"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
        module.exit_json(**sc_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
