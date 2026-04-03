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
module: dedicated_server_ipxe
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Manage iPXE boot feature on dedicated servers
description: >
    Activate or deactivate the public or private iPXE boot feature on a
    dedicated server. Optionally update the iPXE configuration script on an
    already activated feature.

extends_documentation_fragment: serverscom.sc_api.api_auth

options:
  server_id:
    type: str
    required: true
    description:
      - ID of the dedicated server.
      - Use M(serverscom.sc_api.dedicated_server_info) to retrieve servers.

  type:
    type: str
    required: true
    choices: ['public', 'private']
    description:
      - Type of iPXE boot feature to manage.
      - C(public) manages the public_ipxe_boot feature.
      - C(private) manages the private_ipxe_boot feature.

  state:
    type: str
    required: true
    choices: ['present', 'absent']
    description:
      - Desired state of the iPXE boot feature.
      - C(present) activates the feature (or updates iPXE config if already active).
      - C(absent) deactivates the feature.

  ipxe_config:
    type: str
    required: false
    description:
      - iPXE script content (max 64 KB).
      - Required when I(state)=C(present).
      - When the feature is already activated the configuration is updated via
        the server update endpoint.

  wait:
    type: int
    required: false
    default: 600
    description:
      - Maximum time in seconds to wait for the feature to reach the desired
        status after activation or deactivation.
      - Set to C(0) to return immediately without waiting.

  update_interval:
    type: int
    required: false
    default: 10
    description:
      - Polling interval in seconds when waiting for the feature status change.
"""

RETURN = """
feature:
  description: Feature object returned by the API.
  type: dict
  returned: on success
  contains:
    name:
      description: Feature name (e.g. public_ipxe_boot, private_ipxe_boot).
      type: str
    status:
      description: >
        Current feature status (activation, activated, deactivation,
        deactivated, incompatible, unavailable).
      type: str
"""

EXAMPLES = """
- name: Activate public iPXE boot
  serverscom.sc_api.dedicated_server_ipxe:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    type: public
    state: present
    ipxe_config: |
      #!ipxe
      chain http://boot.example.com/menu.ipxe

- name: Activate private iPXE boot with custom config
  serverscom.sc_api.dedicated_server_ipxe:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    type: private
    state: present
    ipxe_config: |
      #!ipxe
      chain http://boot.example.com/menu.ipxe

- name: Update iPXE config on already activated feature
  serverscom.sc_api.dedicated_server_ipxe:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    type: public
    state: present
    ipxe_config: |
      #!ipxe
      chain http://boot.example.com/new-menu.ipxe

- name: Deactivate public iPXE boot
  serverscom.sc_api.dedicated_server_ipxe:
    token: "{{ api_token }}"
    server_id: "0m592Zmn"
    type: public
    state: absent
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    AUTH_ARGS,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.dedicated_server import (
    ScDedicatedServerIpxe,
)


def main():
    module = AnsibleModule(
        argument_spec={
            **AUTH_ARGS,
            "server_id": {"type": "str", "required": True},
            "type": {
                "type": "str",
                "choices": ["public", "private"],
                "required": True,
            },
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "required": True,
            },
            "ipxe_config": {"type": "str", "no_log": False},
            "wait": {"type": "int", "default": 600},
            "update_interval": {"type": "int", "default": 10},
        },
        required_if=[
            ["state", "present", ["ipxe_config"]],
        ],
        supports_check_mode=True,
    )

    try:
        ipxe = ScDedicatedServerIpxe(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params["server_id"],
            ipxe_type=module.params["type"],
            state=module.params["state"],
            ipxe_config=module.params["ipxe_config"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
        module.exit_json(**ipxe.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
