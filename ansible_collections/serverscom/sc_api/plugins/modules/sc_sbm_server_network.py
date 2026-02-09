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
module: sc_sbm_server_network
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Create or delete a network for an SBM (Scalable Baremetal) server
description: >
    Create a private IPv4 network or delete an existing network
    for a Scalable Baremetal server.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
    server_id:
      type: str
      required: true
      description:
        - ID of the SBM server.

    state:
      type: str
      required: true
      choices: [present, absent]
      description:
        - C(present) creates a new private IPv4 network.
        - C(absent) deletes an existing network.

    network_id:
      type: str
      description:
        - ID of the network to delete.
        - Required when I(state=absent).

    mask:
      type: int
      description:
        - Subnet mask for the new network (/29 to /26).
        - Required when I(state=present).

    distribution_method:
      type: str
      choices: [gateway]
      default: gateway
      description:
        - Distribution method for the new network.
        - Only C(gateway) is available.

    wait:
      type: int
      default: 600
      description:
        - Time to wait (in seconds) for the network to reach desired state.
        - For I(state)=C(present), waits for the network to become C(active)
          (CIDR is assigned once active).
        - For I(state)=C(absent), waits for the network to be fully removed.
        - Value C(0) disables waiting (fire-and-forget mode).

    update_interval:
      type: int
      default: 10
      description:
        - Polling interval (in seconds) while waiting.
        - Every polling request reduces API rate limits.
"""

RETURN = """
id:
  type: str
  description:
    - Network ID.
  returned: on success

status:
  type: str
  description:
    - Network status.
  returned: on success

cidr:
  type: str
  description:
    - Network CIDR.
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
- name: Create a private IPv4 /29 network (waits for active)
  serverscom.sc_api.sc_sbm_server_network:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
    state: present
    mask: 29
  register: network

- name: Create a network without waiting
  serverscom.sc_api.sc_sbm_server_network:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
    state: present
    mask: 29
    wait: 0
  register: network

- name: Delete a network
  serverscom.sc_api.sc_sbm_server_network:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
    state: absent
    network_id: 'net456'
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerNetwork,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "server_id": {"type": "str", "required": True},
            "state": {
                "type": "str",
                "required": True,
                "choices": ["present", "absent"],
            },
            "network_id": {"type": "str"},
            "mask": {"type": "int"},
            "distribution_method": {
                "type": "str",
                "choices": ["gateway"],
                "default": "gateway",
            },
            "wait": {"type": "int", "default": 600},
            "update_interval": {"type": "int", "default": 10},
        },
        required_if=[
            ("state", "present", ["mask"]),
            ("state", "absent", ["network_id"]),
        ],
        supports_check_mode=True,
    )
    try:
        network = ScSbmServerNetwork(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params["server_id"],
            state=module.params["state"],
            network_id=module.params["network_id"],
            mask=module.params["mask"],
            distribution_method=module.params["distribution_method"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
        module.exit_json(**network.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
