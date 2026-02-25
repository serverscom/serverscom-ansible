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
module: sc_l2_segment_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Information about L2 segment.
description: >
    Returns information about exiting L2 segment or fail.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    id:
      type: str
      description:
        - ID of the L2 segement
        - Either I(name) or I(id) is required

    name:
      type: str
      description:
        - Name of the L2 segment
        - Either I(name) or I(id) is required

"""

RETURN = """
l2_segment:
  type: complex
  returned: on success
  description:
    - Information about a single L2 segment.
  contains:
    id:
      type: str
      description:
        - Unique identifier of the L2 segment.
    name:
      type: str
      description:
        - Name of the L2 segment.
    type:
      type: str
      description:
        - "Segment type: 'public' or 'private'."
    status:
      type: str
      description:
        - "Segment state: 'pending' – creating; 'active' – ready to use; 'removing' – deleting."
    location_group_id:
      type: int
      description:
        - Identifier of the location group.
    location_group_code:
      type: str
      description:
        - Technical code of the location group.
    labels:
      type: dict
      description:
        - Labels attached to the segment.
    created_at:
      type: str
      description:
        - Creation timestamp.
    updated_at:
      type: str
      description:
        - Last update timestamp; null if never updated.

api_url:
  type: str
  returned: on failure
  description:
    - URL of the failed request.

status_code:
  type: int
  returned: always
  description:
    - HTTP status code of the response.
"""

EXAMPLES = """
- name: Gather information about existing L2 segments
  serverscom.sc_api.sc_l2_segment_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    id: 'WZdPwbKg'
  register: sc_l2_seg

- name: Print all locations
  debug: var=sc_l2_seg.l2_segment
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScL2SegmentInfo,
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "id": {},
            "name": {},
        },
        required_one_of=[["id", "name"]],
        supports_check_mode=True,
    )
    try:
        sc_info = ScL2SegmentInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            id=module.params["id"],
            name=module.params["name"],
        )
        module.exit_json(**sc_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
