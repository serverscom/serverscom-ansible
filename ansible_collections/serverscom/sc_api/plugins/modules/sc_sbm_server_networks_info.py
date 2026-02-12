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
module: sc_sbm_server_networks_info
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: List or get networks for an SBM (Scalable Baremetal) server
description: >
    Returns a list of networks for a Scalable Baremetal server, or
    details of a single network if network_id is provided.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
    server_id:
      type: str
      description:
        - ID of the SBM server.
        - Mutually exclusive with I(hostname).

    hostname:
      type: str
      description:
        - Hostname of the SBM server (exact match on server title).
        - Mutually exclusive with I(server_id).

    network_id:
      type: str
      description:
        - ID of a specific network to retrieve.
        - If provided, returns details of that single network.
        - If omitted, returns list of all networks.

    search_pattern:
      type: str
      description:
        - Filter networks by search pattern.

    family:
      type: str
      choices: [ipv4, ipv6]
      description:
        - Filter networks by IP family.

    interface_type:
      type: str
      choices: [public, private, oob]
      description:
        - Filter networks by interface type.

    distribution_method:
      type: str
      choices: [route, gateway]
      description:
        - Filter networks by distribution method.

    additional:
      type: bool
      description:
        - Filter by whether the network is an additional (non-default) network.
"""

RETURN = """
networks:
  type: list
  description:
    - List of networks for the server (when network_id is not provided).
  returned: on success when listing

id:
  type: str
  description:
    - Network ID (when network_id is provided).
  returned: on success when getting single network

cidr:
  type: str
  description:
    - Network CIDR (when network_id is provided).
  returned: on success when getting single network

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
- name: List all networks for an SBM server
  serverscom.sc_api.sc_sbm_server_networks_info:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
  register: networks

- name: List only private IPv4 networks
  serverscom.sc_api.sc_sbm_server_networks_info:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
    family: ipv4
    interface_type: private
  register: private_nets

- name: Get specific network details
  serverscom.sc_api.sc_sbm_server_networks_info:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
    network_id: 'net456'
  register: network
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    ScApi,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerNetworksInfo,
    resolve_sbm_server_id,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "server_id": {"type": "str"},
            "hostname": {"type": "str"},
            "network_id": {"type": "str"},
            "search_pattern": {"type": "str"},
            "family": {"type": "str", "choices": ["ipv4", "ipv6"]},
            "interface_type": {"type": "str", "choices": ["public", "private", "oob"]},
            "distribution_method": {"type": "str", "choices": ["route", "gateway"]},
            "additional": {"type": "bool"},
        },
        required_one_of=[["server_id", "hostname"]],
        mutually_exclusive=[["server_id", "hostname"]],
        supports_check_mode=True,
    )
    try:
        api = ScApi(module.params["token"], module.params["endpoint"])
        server_id = resolve_sbm_server_id(
            api,
            server_id=module.params["server_id"],
            hostname=module.params["hostname"],
        )
        networks_info = ScSbmServerNetworksInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=server_id,
            network_id=module.params["network_id"],
            search_pattern=module.params["search_pattern"],
            family=module.params["family"],
            interface_type=module.params["interface_type"],
            distribution_method=module.params["distribution_method"],
            additional=module.params["additional"],
        )
        module.exit_json(**networks_info.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
