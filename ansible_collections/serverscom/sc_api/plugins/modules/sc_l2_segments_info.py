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
module: sc_l2_segments_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Information about existing L2 segments.
description: >
    Returns all L2 segments

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    label_selector:
        type: str
        description:
            - Search for bare metal servers with specific labels.
            - More info at https://developers.servers.com/api-documentation/v1/#section/Labels/Labels-selector
"""

RETURN = """
l2_segments:
  type: list
  elements: dict
  returned: on success
  description:
    - List of L2 segments.
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
        - "'pending' – creating;"
        - "'active' – ready to use;"
        - "'removing' – deleting."
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
  serverscom.sc_api.sc_l2_segments_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
  register: sc_l2

- name: Print all locations
  debug: var=item.name
  with_items: '{{ sc_l2.l2_segments }}'
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScL2SegmentsInfo,
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "label_selector": {"type": "str"},
        },
        supports_check_mode=True,
    )
    try:
        sc_info = ScL2SegmentsInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            label_selector=module.params.get("label_selector"),
        )
        module.exit_json(**sc_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
