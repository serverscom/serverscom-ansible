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
module: dedicated_server_rescue
version_added: "1.1.0"
author: "Aleksandr Chudinov (@chal)"
short_description: Manage rescue mode on a Bare Metal server
description: >
    Activate or deactivate rescue mode on a Bare Metal (dedicated) server.
    Rescue mode boots the server into a temporary environment for
    troubleshooting and recovery. The server's disks are not mounted
    automatically.

extends_documentation_fragment: serverscom.sc_api.api_auth

options:
  server_id:
    type: str
    required: true
    description:
      - ID of the Bare Metal server.
      - Use I(serverscom.sc_api.baremetal_servers_info) to retrieve servers.

  state:
    type: str
    required: true
    choices: ['rescue', 'normal']
    description:
      - Desired rescue mode state.
      - "I(rescue): activate rescue mode."
      - "I(normal): deactivate rescue mode and boot normally."

  auth_methods:
    type: list
    elements: str
    description:
      - Authentication methods for rescue mode login.
      - Required when I(state)=C(rescue).
      - "C(password): enable password authentication."
      - "C(ssh_key): enable SSH key authentication
        (requires I(ssh_key_fingerprints) or I(ssh_key_name))."

  ssh_key_fingerprints:
    type: list
    elements: str
    description:
      - Fingerprints of SSH keys for rescue mode access.
      - Required when C(ssh_key) is in I(auth_methods).
      - Keys must be registered via M(serverscom.sc_api.ssh_key).
      - Mutually exclusive with I(ssh_key_name).

  ssh_key_name:
    type: str
    description:
      - Name of a single SSH key to use for rescue mode access.
      - The module resolves the name to a fingerprint via the SSH keys API.
      - Mutually exclusive with I(ssh_key_fingerprints).

  wait:
    type: int
    default: 600
    description:
      - Maximum time in seconds to wait for the server to reach the
        desired operational status.
      - Set to C(0) to disable waiting.

  update_interval:
    type: int
    default: 10
    description:
      - Polling interval in seconds when waiting.
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
- name: Activate rescue mode with password auth
  serverscom.sc_api.dedicated_server_rescue:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: rescue
    auth_methods:
      - password

- name: Activate rescue mode with SSH key by name
  serverscom.sc_api.dedicated_server_rescue:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: rescue
    auth_methods:
      - ssh_key
    ssh_key_name: my-key

- name: Activate rescue mode with SSH key by fingerprint
  serverscom.sc_api.dedicated_server_rescue:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: rescue
    auth_methods:
      - password
      - ssh_key
    ssh_key_fingerprints:
      - "ab:cd:ef:12:34:56:78:90"

- name: Deactivate rescue mode
  serverscom.sc_api.dedicated_server_rescue:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: normal

- name: Activate rescue without waiting
  serverscom.sc_api.dedicated_server_rescue:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    state: rescue
    auth_methods:
      - password
    wait: 0
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    AUTH_ARGS,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server import (
    ScDedicatedServerRescue,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            **AUTH_ARGS,
            "server_id": {"type": "str", "required": True},
            "state": {
                "type": "str",
                "choices": ["rescue", "normal"],
                "required": True,
            },
            "auth_methods": {
                "type": "list",
                "elements": "str",
            },
            "ssh_key_fingerprints": {
                "type": "list",
                "elements": "str",
                "no_log": False
            },
            "ssh_key_name": {"type": "str"},
            "wait": {"type": "int", "default": 600},
            "update_interval": {"type": "int", "default": 10},
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ["ssh_key_fingerprints", "ssh_key_name"],
        ],
        required_if=[
            ["state", "rescue", ["auth_methods"]],
        ],
    )

    try:
        rescue = ScDedicatedServerRescue(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params["server_id"],
            state=module.params["state"],
            auth_methods=module.params["auth_methods"],
            ssh_key_fingerprints=module.params["ssh_key_fingerprints"],
            ssh_key_name=module.params["ssh_key_name"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
        module.exit_json(**rescue.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
