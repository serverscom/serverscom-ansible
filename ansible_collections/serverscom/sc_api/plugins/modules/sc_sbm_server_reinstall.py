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
module: sc_sbm_server_reinstall
version_added: "1.0.0"
author: "Vil Surkin (@vills)"
short_description: Reinstall SBM (Scalable Baremetal) server.
description: >
    Reinstall the existing Scalable Baremetal server. Existing data may be lost in
    the process. No secure erase or wipe is performed during installation.
    Note that SBM servers do not support custom drive layouts - the disk
    configuration is managed automatically.

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

    server_id:
      aliases: [id, name]
      type: str
      required: true
      description:
        - ID of the SBM server to reinstall.

    hostname:
      type: str
      description:
        - Hostname for the server.
        - Module will retrieve old server title if not specified.

    operating_system_id:
      type: int
      description:
        - ID of the operating system to install on the server.
        - Module will retrieve and reuse old operating system if
          not specified.
        - Mutually exclusive with I(operating_system_regex).

    operating_system_regex:
      type: str
      description:
        - Regular expression to filter operating systems by name.
        - If specified, the module will install operating system
          that matches the provided regex (case insensitive).
        - Mutually exclusive with I(operating_system_id).

    ssh_keys:
      type: list
      elements: str
      description:
        - Array of fingerprints of public ssh keys to add for root user.
        - Keys must be registered before use by module M(serverscom.sc_api.sc_ssh_key).
        - Mutually exclusive with I(ssh_key_name).
        - Server is reinstalled with root password only if no I(ssh_keys) or
          I(ssh_key_name) specified.

    ssh_key_name:
      type: str
      description:
        - Name of a single ssh key to add to root user.
        - Mutually exclusive with I(ssh_keys).
        - Server is reinstalled with root password only if no I(ssh_keys) or
          I(ssh_key_name) specified.
        - Name is used to search fingerprint through ssh keys API requests.
        - Key should be registered.

    wait:
        type: int
        default: 86400
        description:
            - Time to wait for server to change status to 'ready'.
            - If wait is 0 or absent, task succeeds after
              sending request to API without waiting.
            - When server becomes 'ready' after reinstallation,
              it can still be in booting state for some time
              and not answer ssh/ping requests.
              Use M(ansible.builtin.wait_for_connection) module
              to wait for the server to become available through ssh.

    update_interval:
        type: int
        default: 60
        description:
            - Interval in seconds for requests for server status.
            - Each update request reduces number of available API
              requests in accordance with ratelimit.
            - Minimal value is 10.
            - Ignored if I(wait)=C(0).

    user_data:
      type: str
      description:
        - User data content that will be processed by cloud-init
          during server's initialization.
"""

RETURN = """
id:
  type: str
  description:
    - Unique identifier of the server.
  returned: on success

title:
  type: str
  description:
    - Display name of the server.
  returned: on success

type:
  type: str
  description:
    - Always 'sbm_server'.
  returned: on success

status:
  type: str
  description:
    - "init: ordered but not provisioned;"
    - "pending: running operation;"
    - "active: ready to use."
  returned: on success

operational_status:
  type: str
  description:
    - "Detailed operation state."
    - "normal: no operations on the server."
    - "provisioning: server is being activated after an order."
    - "installation: OS reinstalling is in progress."
  returned: on success

power_status:
  type: str
  description:
    - "unknown: during provisioning or on error;"
    - "powering_on: transitional status;"
    - "powered_on: power is on;"
    - "powering_off: transitional status;"
    - "powered_off: power is off;"
    - "power_cycling: power reboot."
  returned: on success

configuration:
  type: str
  description:
    - Chassis model, RAM and disk info.
  returned: on success

location_id:
  type: int
  description:
    - Identifier of the server location.
  returned: on success

location_code:
  type: str
  description:
    - Technical code of the location.
  returned: on success

private_ipv4_address:
  type: str
  description:
    - Private-network IPv4.
    - May be null.
  returned: on success

public_ipv4_address:
  type: str
  description:
    - Public-network IPv4.
    - May be null.
  returned: on success

configuration_details:
  type: complex
  description:
    - Structured server configuration.
  contains:
    ram_size:
      type: int
      description:
        - RAM size in MB.
        - May be null.
    sbm_flavor_model_id:
      type: int
      description:
        - Identifier of the SBM flavor model.
        - May be null.
    sbm_flavor_model_name:
      type: str
      description:
        - Human-readable SBM flavor model name.
        - May be null.
    operating_system_id:
      type: int
      description:
        - Identifier of installed OS.
        - May be null.
    operating_system_full_name:
      type: str
      description:
        - Full name of installed OS.
        - May be null.
  returned: on success

labels:
  type: dict
  description:
    - Labels attached to the server.
  returned: on success

created_at:
  type: str
  description:
    - Creation timestamp.
  returned: on success

updated_at:
  type: str
  description:
    - Last update timestamp.
  returned: on success

ready:
  type: bool
  description:
    - True when status='active', power_status='powered_on', operational_status='normal'.
  returned: on success when wait > 0

elapsed:
  type: float
  description:
    - Time in seconds spent waiting for the server to become ready.
  returned: on success when wait > 0
"""

EXAMPLES = """
- name: Reinstall SBM server with specific OS
  serverscom.sc_api.sc_sbm_server_reinstall:
    token: "{{ sc_token }}"
    server_id: 'abc123xyz'
    operating_system_id: 49
    hostname: my-sbm-server
    wait: 0

- name: Reinstall SBM server using OS regex
  serverscom.sc_api.sc_sbm_server_reinstall:
    token: "{{ sc_token }}"
    server_id: 'abc123xyz'
    operating_system_regex: 'Ubuntu 22'
    hostname: my-sbm-server
    ssh_key_name: my-key
    wait: 3600

- name: Reinstall keeping current OS
  serverscom.sc_api.sc_sbm_server_reinstall:
    token: "{{ sc_token }}"
    server_id: 'abc123xyz'
    ssh_keys:
      - 'aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99'
    wait: 3600
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerReinstall,
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "server_id": {"type": "str", "required": True, "aliases": ["id", "name"]},
            "hostname": {"type": "str"},
            "operating_system_id": {"type": "int"},
            "operating_system_regex": {"type": "str"},
            "ssh_keys": {"type": "list", "elements": "str", "no_log": False},
            "ssh_key_name": {"type": "str"},
            "wait": {"type": "int", "default": 86400},
            "update_interval": {"type": "int", "default": 60},
            "user_data": {"type": "str"},
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ["ssh_keys", "ssh_key_name"],
            ["operating_system_id", "operating_system_regex"],
        ],
    )
    try:
        sc_sbm_server_reinstall = ScSbmServerReinstall(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params["server_id"],
            hostname=module.params["hostname"],
            operating_system_id=module.params["operating_system_id"],
            operating_system_regex=module.params["operating_system_regex"],
            ssh_keys=module.params["ssh_keys"],
            ssh_key_name=module.params["ssh_key_name"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            user_data=module.params["user_data"],
            checkmode=module.check_mode,
        )
        module.exit_json(**sc_sbm_server_reinstall.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
