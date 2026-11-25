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
module: bgp_group_info
version_added: "1.3.0"
author: "Servers.com Team (@serverscom)"
short_description: Information about a BGP group
description: >
    Returns information about a single BGP group, found by id or by name.
    Fails if the group is not found.
extends_documentation_fragment: serverscom.sc_api.api_auth

options:
    bgp_group_id:
      type: str
      description:
        - ID of the BGP group.
        - Mutually exclusive with I(name).
    name:
      type: str
      description:
        - Name of the BGP group (exact match).
        - Mutually exclusive with I(bgp_group_id).
"""

RETURN = """
bgp_group:
  type: dict
  returned: on success
  description: BGP group.
  contains:
    id:
      type: str
      description: ID of the BGP group.
    name:
      type: str
      description: Name of the BGP group.
    network_type:
      type: str
      description: Network type (C(public) or C(private)).
    asn:
      type: int
      description: Session ASN.
    session_type:
      type: str
      description: Session type (C(ibgp) or C(ebgp)).
    status:
      type: str
      description: Group status (C(pending), C(active), C(removing), C(failed)).
    location_ids:
      type: list
      elements: int
      description: Location IDs of the group.
    hosts:
      type: list
      elements: dict
      description: Hosts of the group (C(server_id), C(location_id)).
    announced_prefixes:
      type: list
      elements: dict
      description:
        - Announced prefixes of the group (C(id), C(prefix), C(mask),
          C(quantity), C(status), C(created_at)).
    max_prefix_limit:
      type: int
      description: Maximum prefix limit (may be null).
    labels:
      type: dict
      description: Labels of the group.
    created_at:
      type: str
      description: Creation time.
    updated_at:
      type: str
      description: Last update time.

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
- name: Get BGP group by name
  serverscom.sc_api.bgp_group_info:
    token: '{{ sc_token }}'
    name: bgp-1
  register: bgp

- name: Show announced prefixes
  debug:
    msg: '{{ bgp.bgp_group.announced_prefixes | map(attribute="prefix") }}'

- name: Get BGP group by id
  serverscom.sc_api.bgp_group_info:
    token: '{{ sc_token }}'
    bgp_group_id: y5eVOMaE
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    AUTH_ARGS,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.bgp import (
    ScBgpGroupInfo,
)


def main():
    module = AnsibleModule(
        argument_spec={
            **AUTH_ARGS,
            "bgp_group_id": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[["bgp_group_id", "name"]],
        mutually_exclusive=[["bgp_group_id", "name"]],
        supports_check_mode=True,
    )
    try:
        info = ScBgpGroupInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            bgp_group_id=module.params["bgp_group_id"],
            name=module.params["name"],
        )
        module.exit_json(**info.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
