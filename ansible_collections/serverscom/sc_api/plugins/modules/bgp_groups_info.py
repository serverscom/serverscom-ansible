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
module: bgp_groups_info
version_added: "1.3.0"
author: "Servers.com Team (@serverscom)"
short_description: List BGP groups
description: >
    Returns a list of BGP groups, optionally filtered.
extends_documentation_fragment: serverscom.sc_api.api_auth

options:
    search_pattern:
      type: str
      description:
        - Return only groups matching the search pattern.
    status:
      type: str
      choices: [pending, active, removing, failed]
      description:
        - Return only groups with this status.
    location_id:
      type: int
      description:
        - Return only groups in this location.
        - Mutually exclusive with I(location_code).
    location_code:
      type: str
      description:
        - Code of the location (for example, C(AMS1)).
        - Mutually exclusive with I(location_id).
    asn:
      type: int
      description:
        - Return only groups with this ASN.
    server_id:
      type: str
      description:
        - Return only groups which have this server as a host.
        - Mutually exclusive with I(hostname).
    hostname:
      type: str
      description:
        - Hostname of the server (exact match on the host title).
        - Mutually exclusive with I(server_id).
    label_selector:
      type: str
      description:
        - Return only groups matching the label selector.
        - More info at U(https://developers.servers.com/api-documentation/v1/#section/Labels/Labels-selector).
"""

RETURN = """
bgp_groups:
  type: list
  elements: dict
  returned: on success
  description:
    - List of BGP groups.
    - See M(serverscom.sc_api.bgp_group_info) for the description of fields.

api_url:
  type: str
  returned: on failure
  description: URL for the failed request.

status_code:
  type: int
  returned: on failure
  description: Status code for the request.
"""

EXAMPLES = """
- name: List all BGP groups
  serverscom.sc_api.bgp_groups_info:
    token: '{{ sc_token }}'
  register: groups

- name: List active BGP groups of a server
  serverscom.sc_api.bgp_groups_info:
    token: '{{ sc_token }}'
    hostname: web-01
    status: active
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    AUTH_ARGS,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.bgp import (
    ScBgpGroupsInfo,
)


def main():
    module = AnsibleModule(
        argument_spec={
            **AUTH_ARGS,
            "search_pattern": {"type": "str"},
            "status": {
                "type": "str",
                "choices": ["pending", "active", "removing", "failed"],
            },
            "location_id": {"type": "int"},
            "location_code": {"type": "str"},
            "asn": {"type": "int"},
            "server_id": {"type": "str"},
            "hostname": {"type": "str"},
            "label_selector": {"type": "str"},
        },
        mutually_exclusive=[
            ["location_id", "location_code"],
            ["server_id", "hostname"],
        ],
        supports_check_mode=True,
    )
    try:
        info = ScBgpGroupsInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            search_pattern=module.params["search_pattern"],
            status=module.params["status"],
            location_id=module.params["location_id"],
            location_code=module.params["location_code"],
            asn=module.params["asn"],
            server_id=module.params["server_id"],
            hostname=module.params["hostname"],
            label_selector=module.params["label_selector"],
        )
        module.exit_json(**info.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
