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
module: sc_cloud_computing_flavors_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: List of available flavors
description: >
    Return list of all available flavors.

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
    region_id:
      type: int
      required: true
      description:
        - Id of cloud computing region.
        - Use I(sc_cloud_computing_regions_info) module to retrive list of
          available regions.
"""

RETURN = """
cloud_flavors:
  type: complex
  description:
    - List of available flavors for region.
  contains:
    id:
      type: str
      description:
        - Id of the flavor.
    name:
      type: str
      description:
        - Human-readable name of the flavor.
    disk:
      type: int
      description:
        - Disk size in GB for this flavor.
    ram:
      type: int
      description:
        - Memory size in MB for this flavor.
    vcpus:
      type: int
      description:
        - Number of CPU allocated for this flavor.
  returned: on success

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
    - name: List all flavors
      sc_cloud_computing_flavors_info:
        token: '{{ sc_token }}'
        region_id: 0
      register: flavors

    - debug: var=flavors.cloud_flavors
"""


from ansible.module_utils.basic import AnsibleModule
import json
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    ModuleError,
    ScCloudComputingFlavorsInfo
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'region_id': {'type': 'int', 'required': True}
        },
        supports_check_mode=True
    )

    flavors = ScCloudComputingFlavorsInfo(
        endpoint=module.params['endpoint'],
        token=module.params['token'],
        region_id=module.params['region_id']
    )
    try:
        module.exit_json(**flavors.run())
    except ModuleError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
