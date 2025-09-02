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
module: sc_rbs_flavors_info
version_added: "1.0.0"
author: "Aleksandr Chudinov (@chal)"
short_description: List of available Remote Block Storage volume flavors.
description: >
    Returns list of available Remote Block Storage volume flavors.

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
    location_id:
      type: int
      required: true
      description:
        - Id of a location.
"""

RETURN = """
rbs_volume_flavors:
  type: complex
  description:
    - List of available flavors for location.
  contains:
    id:
      type: str
      description:
        - Unique flavor identifier
    name:
      type: str
      description:
        - Flavor display name
    iops_per_gb:
      type: float
      description:
        - IOPS per GB for this flavor
    bandwidth_per_gb:
      type: float
      description:
        - Bandwidth per GB of volume size in MB/s, for this flavor
    min_size_gb:
      type: int
      description:
        - Minimum volume size in GB for this flavor
  returned: on success
api_url:
    description: URL for the failed request
    returned: on failure
    type: str
status_code:
    description: Status code for the request
    returned: on failure
    type: int
"""

EXAMPLES = """
    - name: List all flavors
      serverscom.sc_api.sc_rbs_flavors_info:
        token: '{{ sc_token }}'
        location_id: 0
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScRBSFlavorsInfo,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT, "required": False},
            "location_id": {"type": "int", "required": True},
        },
        supports_check_mode=True,
    )
    try:
        flavors = ScRBSFlavorsInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            location_id=module.params["location_id"],
        )
        module.exit_json(**flavors.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
