#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2025, Servers.com
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
module: sc_dedicated_server_power
version_added: "1.0.0"
author: "Volodymyr Rudniev (@koef)"
short_description: Power on/off Bare Metal server
description: >
    Manage the power state of a Bare Metal server outlet. Power on will start
    the server only if OOB configured accordingly.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
  server_id:
    type: str
    required: true
    description:
      - ID of the Bare Metal server.
      - Use I(serverscom.sc_api.sc_baremetal_servers_info) to retrieve servers.

  state:
    type: str
    required: true
    choices: ['on', 'off', 'cycle']
    description:
      - Desired power state.
      - "I(on): power on outlet."
      - "I(off): power off outlet."
      - "I(cycle): power cycle outlet. Within this action the power will be
        turned off and then on again. This is equivalent to unplugging the
        power cord and plugging it back in."

  wait:
    description:
      - |
        Maximum time in seconds to wait for the server to reach the desired state."
    required: false
    type: int
    default: 60
"""

RETURN = """
id:
  description: Unique identifier of a server.
  type: str
  returned: on success

title:
  description: Displayed name of the server (defaults to hostname).
  type: str
  returned: on success

type:
  description: "Resource type (always 'dedicated_server')."
  type: str
  returned: on success

rack_id:
  description: Unique identifier of the rack, or null if provisioning.
  type: str
  returned: on success

status:
  description: Provisioning state of the server (init, pending, active).
  type: str
  returned: on success

operational_status:
  description: Detailed operational state (normal, provisioning, installation, entering_rescue_mode, rescue_mode, exiting_rescue_mode).
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

lease_start_at:
  description: Date when leasing began, or null.
  type: str
  returned: on success

scheduled_release_at:
  description: Scheduled release date-time, or null.
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

oob_ipv4_address:
  description: Out-of-band IPv4 address if OOB access is enabled, or null.
  type: str
  returned: on success
"""

EXAMPLES = """
- name: Power off server
  sc_dedicated_server_power:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: off

- name: Power on server
  sc_dedicated_server_power:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: on

# power cycle server (disable and enable power)
- name: Cycle power on server
  sc_dedicated_server_power:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: cycle

- name: Wait until server is powered off
  wait_for:
    host: "{{ hostvars[inventory_hostname].ansible_host }}"
    port: 22
    state: drained
    timeout: 30

- name: Wait for SSH login
  wait_for_connection:
    connect_timeout: 5
    timeout: 600

- name: Re-gather facts after reboot
  setup:
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_dedicated_server import (
    ScDedicatedServerPower,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "token": {"type": "str", "no_log": True, "required": True},
            "server_id": {"type": "str", "required": True},
            "state": {
                "type": "str",
                "choices": ["on", "off", "cycle"],
                "required": True,
            },
            "wait": {"type": "int", "default": 60},
        },
        supports_check_mode=True,
    )

    try:
        power = ScDedicatedServerPower(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params["server_id"],
            state=module.params["state"],
            wait=module.params["wait"],
            checkmode=module.check_mode,
        )
        module.exit_json(**power.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
