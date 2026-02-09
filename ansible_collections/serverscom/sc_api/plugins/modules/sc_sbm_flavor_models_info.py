#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2026, Servers.com
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
module: sc_sbm_flavor_models_info
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: List of available SBM (Scalable Baremetal) flavor models.
description: >
    Returns list of available Scalable Baremetal flavor models for a location.
    These flavor models define the hardware configurations available for SBM servers.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
    location_id:
      type: int
      required: true
      description:
        - ID of a location to list SBM flavor models for.
        - Use M(serverscom.sc_api.sc_baremetal_locations_info) to get location IDs.

    search_pattern:
      type: str
      description:
        - Filter flavor models by name pattern.
        - Case-insensitive partial match.
"""

RETURN = """
sbm_flavor_models:
  type: list
  description:
    - List of available SBM flavor models for the location.
  returned: on success
  contains:
    id:
      type: int
      description:
        - Unique identifier of the SBM flavor model.
    name:
      type: str
      description:
        - Name of the SBM flavor model.
    cpu_description:
      type: str
      description:
        - CPU description.
    ram_size:
      type: int
      description:
        - RAM size in MB.
    drives_description:
      type: str
      description:
        - Description of the drive configuration.

api_url:
    description: URL for the failed request.
    returned: on failure
    type: str

status_code:
    description: Status code for the request.
    returned: on failure
    type: int
"""

EXAMPLES = """
- name: List all SBM flavor models for a location
  serverscom.sc_api.sc_sbm_flavor_models_info:
    token: '{{ sc_token }}'
    location_id: 1
  register: flavors

- name: Display available SBM flavors
  debug:
    msg: "{{ item.name }}: {{ item.cpu_description }}, {{ item.ram_size }}MB RAM"
  loop: "{{ flavors.sbm_flavor_models }}"

- name: Search for specific flavor model
  serverscom.sc_api.sc_sbm_flavor_models_info:
    token: '{{ sc_token }}'
    location_id: 1
    search_pattern: 'AMD'
  register: amd_flavors
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmFlavorModelsInfo,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "location_id": {"type": "int", "required": True},
            "search_pattern": {"type": "str"},
        },
        supports_check_mode=True,
    )
    try:
        flavors = ScSbmFlavorModelsInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            location_id=module.params["location_id"],
            search_pattern=module.params["search_pattern"],
        )
        module.exit_json(**flavors.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
