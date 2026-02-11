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
module: sc_sbm_server_power
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Power on/off SBM (Scalable Baremetal) server
description: >
    Manage the power state of a Scalable Baremetal server outlet.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
  server_id:
    type: str
    description:
      - ID of the SBM server.
      - Mutually exclusive with I(hostname).
      - Use I(serverscom.sc_api.sc_baremetal_servers_info) with type=sbm_server to retrieve servers.

  hostname:
    type: str
    description:
      - Hostname of the SBM server (exact match on server title).
      - Mutually exclusive with I(server_id).

  state:
    type: str
    required: true
    choices: ['on', 'off', 'cycle']
    description:
      - Desired power state.
      - "I(on): power on outlet."
      - "I(off): power off outlet."
      - "I(cycle): power cycle outlet. Within this action the power will be
        turned off and then on again."

  wait:
    description:
      - |
        Maximum time in seconds to wait for the server to reach the desired state.
    required: false
    type: int
    default: 180
"""

RETURN = """
id:
  description: Unique identifier of the server.
  type: str
  returned: on success

title:
  description: Displayed name of the server (defaults to hostname).
  type: str
  returned: on success

type:
  description: "Resource type (always 'sbm_server')."
  type: str
  returned: on success

status:
  description: Provisioning state of the server (init, pending, active).
  type: str
  returned: on success

operational_status:
  description: Detailed operational state (normal, provisioning, installation).
  type: str
  returned: on success

power_status:
  description: Power state indicator (unknown, powering_on, powered_on, powering_off, powered_off, power_cycling).
  type: str
  returned: on success

configuration:
  description: Chassis model, RAM, and disk details.
  type: str
  returned: on success

location_id:
  description: Numeric identifier of the server's location.
  type: int
  returned: on success

location_code:
  description: Technical code of the server's location.
  type: str
  returned: on success

private_ipv4_address:
  description: Private IPv4 address, or null if unassigned.
  type: str
  returned: on success

public_ipv4_address:
  description: Public IPv4 address, or null if unassigned.
  type: str
  returned: on success

configuration_details:
  description: Detailed configuration object.
  type: dict
  returned: on success

labels:
  description: Labels associated with the server resource.
  type: dict
  returned: on success

created_at:
  description: Timestamp when the server was created.
  type: str
  returned: on success

updated_at:
  description: Timestamp of the last update.
  type: str
  returned: on success
"""

EXAMPLES = """
- name: Power off SBM server by ID
  serverscom.sc_api.sc_sbm_server_power:
    token: "{{ sc_token }}"
    server_id: "abc123xyz"
    state: off

- name: Power on SBM server by hostname
  serverscom.sc_api.sc_sbm_server_power:
    token: "{{ sc_token }}"
    hostname: my-sbm-server
    state: on

- name: Cycle power on SBM server
  serverscom.sc_api.sc_sbm_server_power:
    token: "{{ sc_token }}"
    server_id: "abc123xyz"
    state: cycle

- name: Wait for SSH login after power on
  wait_for_connection:
    connect_timeout: 5
    timeout: 600
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    ScApi,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerPower,
    resolve_sbm_server_id,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "token": {"type": "str", "no_log": True, "required": True},
            "server_id": {"type": "str"},
            "hostname": {"type": "str"},
            "state": {
                "type": "str",
                "choices": ["on", "off", "cycle"],
                "required": True,
            },
            "wait": {"type": "int", "default": 180},
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
        power = ScSbmServerPower(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=server_id,
            state=module.params["state"],
            wait=module.params["wait"],
            checkmode=module.check_mode,
        )
        module.exit_json(**power.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
