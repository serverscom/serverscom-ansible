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
module: sc_info
version_added: "2.10"
author: "George Shuklin (@amarao)"
short_description: Information about available locations and regions.
description: >
    Module gathers information about available locations
    for baremetal servers and cloud regions.

options:
    scope:
      type: str
      choices: [all, locations, regions]
      default: all
      description:
        - Scope of query
        - C(locations) limit query to baremetal locations
        - C(regions) limit query to cloud regions.
        - C(all) query both baremetal locations and cloud regions.

    search_pattern:
        type: str
        description:
            - Search substring in locations names.
            - Case insensitive.

    required_features:
        type: list
        description:
            - Filter locations based on features.
            - Seach both top-level features and supported_features.
            - If more than one element specified, search for all of them
              ('and' operation).
        elements: str

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
locations:
    description:
        - List of locations for baremetal servers
        - May contain additional flags for features for location
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

        supported_features:
            type: list
            description:
                - List of supported features
            example:
                - disaggregated_public_ports
                - disaggregated_private_ports
                - no_public_network
                - no_private_ip
                - host_rescue_mode
                - oob_public_access

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
  serverscom.sc_api.sc_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
  register: sc_info

- name: Print all locations
  debug: var=item.name
  with_items: '{{ sc_info.locations }}'

- name: Print all regions
  debug: var=item.name
  with_items: '{{ sc_info.regions }}'

- name: Print remaining API request count
  debug: var=sc_info.limits.remaining
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    DEFAULT_API_ENDPOINT,
    ModuleError,
    ScInfo
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'scope': {
                'type': 'str',
                'choices': ['all', 'locations', 'regions'],
                'default': 'all'
            },
            'search_pattern': {'type': 'str'},
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'required_features': {'type': 'list'},
        },
        supports_check_mode=True
    )
    sc_info = ScInfo(
        endpoint=module.params['endpoint'],
        token=module.params['token'],
        scope=module.params['scope'],
        search_pattern=module.params['search_pattern'],
        required_features=module.params['required_features'],
    )
    try:
        module.exit_json(**sc_info.run())
    except ModuleError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
