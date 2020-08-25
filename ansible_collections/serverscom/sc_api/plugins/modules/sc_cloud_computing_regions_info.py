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
module: sc_cloud_computing_regions_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Information about available cloud computing regions.
description: >
    Module searches for computing cloud regions.

options:
    search_pattern:
        type: str
        description:
            - Search for substring in regions names and codes.
            - Case insensitive.

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
"""

RETURN = """
regions:
    description: List of cloud compute regions
    returned: on success
    type: complex
    contains:
        id:
            type: str
            description:
                - ID of the location.
        name:
            type: str
            description:
                - Name of the location.

        code:
            type: str
            description:
                - Code for the location.
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
- name: Gather information for avaliable regions
  serverscom.sc_api.sc_cloud_computing_regions_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
  register: sc_info

- name: Print all regions
  debug: var=item.name
  with_items: '{{ sc_info.regions }}'

- name: Search for region
  serverscom.sc_api.sc_cloud_computing_regions_info:
    search_pattern: 'WAS'
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    DEFAULT_API_ENDPOINT,
    ModuleError,
    ScCloudComputingRegionsInfo
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'search_pattern': {'type': 'str'},
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
        },
        supports_check_mode=True
    )
    sc_info = ScCloudComputingRegionsInfo(
        endpoint=module.params['endpoint'],
        token=module.params['token'],
        search_pattern=module.params['search_pattern'],
    )
    try:
        module.exit_json(**sc_info.run())
    except ModuleError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
