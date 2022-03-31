#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2020, Servers.com
# GNU General Public License v3.0
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = """
---
module: sc_l2_segment_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Information about L2 segment.
description: >
    Returns information about exiting L2 segment or fail.

options:
    endpoint:
      type: str
      default: https://api.servers.com/v1
      description:
        - Endpoint to use to connect to API.
        - Do not change until specifically asked to do otherwise.

    token:
      type: str
      required: true
      description:
        - Token to use.
        - You can create token for you account in https://portal.servers.com
          in Profile -> Public API section.
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
    ScL2SegmentInfo
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'id': {},
            'name': {}
        },
        required_one_of=[['id', 'name']],
        supports_check_mode=True
    )
    try:
        sc_info = ScL2SegmentInfo(
            endpoint=module.params['endpoint'],
            token=module.params['token'],
            id=module.params['id'],
            name=module.params['name']
        )
        module.exit_json(**sc_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
