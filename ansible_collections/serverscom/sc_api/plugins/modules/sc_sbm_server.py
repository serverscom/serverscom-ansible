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
module: sc_sbm_server
version_added: "1.0.0"
author: "Vil Surkin (@vills)"
short_description: Create or delete an SBM (Scalable Baremetal) server
description: >
    Allow to create (order) or delete (release) a Scalable Baremetal server.

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
        - You can create token for your account in https://portal.servers.com
          in Profile -> Public API section.

    state:
      type: str
      choices: [present, absent]
      required: true
      description:
        - State of the SBM server.
        - C(present) orders a new SBM server.
        - C(absent) releases (deletes) an existing SBM server.
        - C(present) requires I(location_id), I(sbm_flavor_model_id),
          I(hostname), and I(operating_system_id).
        - C(absent) requires I(server_id).

    server_id:
      type: str
      description:
        - ID of the SBM server for I(state)=C(absent).

    location_id:
      type: int
      description:
        - ID of the location to order the server in.
        - Required for I(state)=C(present).

    sbm_flavor_model_id:
      type: int
      description:
        - ID of the SBM flavor model to order.
        - Required for I(state)=C(present).

    hostname:
      type: str
      description:
        - Hostname for the new server.
        - Required for I(state)=C(present).

    operating_system_id:
      type: int
      description:
        - ID of the operating system to install.
        - Required for I(state)=C(present).

    ssh_key_fingerprints:
      type: list
      elements: str
      description:
        - List of SSH key fingerprints to install on the server.

    user_data:
      type: str
      description:
        - User data to pass to the newly created server.

    wait:
      type: int
      default: 86400
      description:
        - Time to wait (in seconds) until server reaches desired state.
        - For I(state)=C(present), waits for server to become ready
          (active, powered_on, normal).
        - For I(state)=C(absent), controls retry timeout when
          I(retry_on_conflicts) is enabled. Does not wait for server
          disappearance unless I(wait_for_deletion) is set.
        - Value C(0) disables waiting (fire-and-forget mode).
        - SBM provisioning can be slow, so the default is 86400 (24 hours).

    update_interval:
      type: int
      default: 60
      description:
        - Polling interval (in seconds) for waiting.
        - Every polling request reduces API rate limits.

    retry_on_conflicts:
      type: bool
      default: true
      description:
        - Retry delete request for I(state)=C(absent) if server
          is in conflicting state (HTTP 409).
        - Retries are controlled by I(wait) and I(update_interval).

    wait_for_deletion:
      type: bool
      default: false
      description:
        - For I(state)=C(absent), whether to wait for the server to
          actually disappear after the delete request is accepted.
        - SBM server deletion is not instant; the server is released
          at the end of the current billing hour.
        - When C(false) (default), the module returns as soon as the
          API accepts the delete request.
        - When C(true), the module polls until the server is gone,
          subject to I(wait) and I(update_interval).
"""

RETURN = """
id:
  type: str
  description:
    - Unique identifier of the SBM server.
  returned: on success

title:
  type: str
  description:
    - Displayed name of the server.
  returned: on success

type:
  type: str
  description:
    - Always 'sbm_server'.
  returned: on success

status:
  type: str
  description:
    - State of the server (init, pending, active).
  returned: on success

operational_status:
  type: str
  description:
    - Maintenance operation status (normal, provisioning, installation).
  returned: on success

power_status:
  type: str
  description:
    - Power state (unknown, powered_on, powered_off, powering_on, powering_off).
  returned: on success

location_id:
  type: int
  description:
    - Unique identifier of the server's location.
  returned: on success

location_code:
  type: str
  description:
    - Technical code of the server's location.
  returned: on success

configuration:
  type: str
  description:
    - Information about chassis model, RAM, and disk drives.
  returned: on success

configuration_details:
  type: complex
  description:
    - Structured server configuration.
  returned: on success
  contains:
    sbm_flavor_model_id:
      type: int
      description: The SBM flavor model ID.
    server_model_id:
      type: str
      description: The server model ID.

public_ipv4_address:
  type: str
  description:
    - IPv4 address on the public network. May be null.
  returned: on success

private_ipv4_address:
  type: str
  description:
    - IPv4 address on the private network. May be null.
  returned: on success

labels:
  type: dict
  description:
    - Labels associated with the server.
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

api_url:
  type: str
  description:
    - URL of the failed request.
  returned: on failure

status_code:
  type: int
  description:
    - HTTP status code of the response.
  returned: on failure
"""

EXAMPLES = """
- name: Create an SBM server
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: present
    location_id: 1
    sbm_flavor_model_id: 42
    hostname: my-sbm-server
    operating_system_id: 100
    wait: 86400
    update_interval: 60
  register: new_server

- name: Delete an SBM server (fire-and-forget)
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: absent
    server_id: '{{ server_id }}'

- name: Delete an SBM server and wait for it to disappear
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: absent
    server_id: '{{ server_id }}'
    wait_for_deletion: true
    wait: 7200
    update_interval: 60
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerCreate,
    ScSbmServerDelete,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "required": True,
            },
            "server_id": {"type": "str"},
            "location_id": {"type": "int"},
            "sbm_flavor_model_id": {"type": "int"},
            "hostname": {"type": "str"},
            "operating_system_id": {"type": "int"},
            "ssh_key_fingerprints": {
                "type": "list",
                "elements": "str",
                "no_log": False,
            },
            "user_data": {"type": "str"},
            "wait": {"type": "int", "default": 86400},
            "update_interval": {"type": "int", "default": 60},
            "retry_on_conflicts": {"type": "bool", "default": True},
            "wait_for_deletion": {"type": "bool", "default": False},
        },
        required_if=[
            [
                "state",
                "present",
                [
                    "location_id",
                    "sbm_flavor_model_id",
                    "hostname",
                    "operating_system_id",
                ],
            ],
            ["state", "absent", ["server_id"]],
        ],
        supports_check_mode=True,
    )
    try:
        if module.params["state"] == "present":
            instance = ScSbmServerCreate(
                endpoint=module.params["endpoint"],
                token=module.params["token"],
                location_id=module.params["location_id"],
                sbm_flavor_model_id=module.params["sbm_flavor_model_id"],
                hostname=module.params["hostname"],
                operating_system_id=module.params["operating_system_id"],
                ssh_key_fingerprints=module.params.get("ssh_key_fingerprints"),
                user_data=module.params.get("user_data"),
                wait=module.params["wait"],
                update_interval=module.params["update_interval"],
                checkmode=module.check_mode,
            )
        elif module.params["state"] == "absent":
            instance = ScSbmServerDelete(
                endpoint=module.params["endpoint"],
                token=module.params["token"],
                server_id=module.params["server_id"],
                wait=module.params["wait"],
                update_interval=module.params["update_interval"],
                retry_on_conflicts=module.params["retry_on_conflicts"],
                wait_for_deletion=module.params["wait_for_deletion"],
                checkmode=module.check_mode,
            )
        else:
            raise NotImplementedError(f"Unsupported state={module.params['state']}.")
        module.exit_json(**instance.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
