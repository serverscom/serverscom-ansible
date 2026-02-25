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
module: sc_sbm_servers_info
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: List SBM (Scalable Baremetal) servers
description: >
    Returns a list of all Scalable Baremetal servers with optional filtering
    by search pattern, location, rack, or labels.
extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    search_pattern:
      type: str
      description:
        - Filter servers by name pattern.

    location_id:
      type: int
      description:
        - Filter servers by location ID.
        - Mutually exclusive with I(location_code).

    location_code:
      type: str
      description:
        - Filter servers by location code (e.g. V(AMS7)).
        - Mutually exclusive with I(location_id).

    rack_id:
      type: str
      description:
        - Filter servers by rack ID.

    label_selector:
      type: str
      description:
        - Filter servers by label selector expression.
"""

RETURN = """
sbm_servers:
  type: list
  description:
    - List of SBM servers.
  returned: on success

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
- name: List all SBM servers
  serverscom.sc_api.sc_sbm_servers_info:
    token: '{{ sc_token }}'
  register: servers

- name: List SBM servers in a location by ID
  serverscom.sc_api.sc_sbm_servers_info:
    token: '{{ sc_token }}'
    location_id: 1
  register: servers

- name: List SBM servers in a location by code
  serverscom.sc_api.sc_sbm_servers_info:
    token: '{{ sc_token }}'
    location_code: AMS7
  register: servers

- name: List SBM servers by label
  serverscom.sc_api.sc_sbm_servers_info:
    token: '{{ sc_token }}'
    label_selector: 'environment=production'
  register: servers
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    ScApi,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServersInfo,
    resolve_location_id,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "search_pattern": {"type": "str"},
            "location_id": {"type": "int"},
            "location_code": {"type": "str"},
            "rack_id": {"type": "str"},
            "label_selector": {"type": "str"},
        },
        mutually_exclusive=[["location_id", "location_code"]],
        supports_check_mode=True,
    )
    try:
        location_id = module.params["location_id"]
        if not location_id and module.params["location_code"]:
            api = ScApi(module.params["token"], module.params["endpoint"])
            location_id = resolve_location_id(
                api,
                location_code=module.params["location_code"],
            )
        servers_info = ScSbmServersInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            search_pattern=module.params["search_pattern"],
            location_id=location_id,
            rack_id=module.params["rack_id"],
            label_selector=module.params["label_selector"],
        )
        module.exit_json(**servers_info.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
