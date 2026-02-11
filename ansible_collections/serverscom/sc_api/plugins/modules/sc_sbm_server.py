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
author: "Servers.com Team (@serverscom)"
short_description: Create or delete an SBM (Scalable Baremetal) server
description: >
    Allow to create (order) or delete (release) a Scalable Baremetal server.
    Note that C(present) always creates a new server and is not idempotent.
    Running the same playbook twice will order two servers.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
    state:
      type: str
      choices: [present, absent]
      required: true
      description:
        - State of the SBM server.
        - C(present) orders a new SBM server.
        - C(absent) releases (deletes) an existing SBM server.
        - C(present) requires I(hostname) and one of each pair
          I(location_id)/I(location_code),
          I(flavor_id)/I(flavor_name),
          I(operating_system_id)/I(operating_system_name)/I(operating_system_regex).
        - C(absent) requires I(server_id) or I(hostname).

    server_id:
      type: str
      description:
        - ID of the SBM server for I(state)=C(absent).
        - Mutually exclusive with I(hostname) when I(state)=C(absent).

    location_id:
      type: int
      description:
        - ID of the location to order the server in.
        - Mutually exclusive with I(location_code).

    location_code:
      type: str
      description:
        - Code of the location to order the server in (e.g. V(AMS7)).
        - Mutually exclusive with I(location_id).

    flavor_id:
      type: int
      description:
        - ID of the SBM flavor model to order.
        - Mutually exclusive with I(flavor_name).

    flavor_name:
      type: str
      description:
        - Human-readable name of the SBM flavor model (e.g. V(DL-01)).
        - Mutually exclusive with I(flavor_id).

    hostname:
      type: str
      description:
        - Hostname for the new server (I(state)=C(present)).
        - Can also be used to identify the server for I(state)=C(absent)
          instead of I(server_id). The hostname is resolved to a server ID
          via exact match on the server title.

    operating_system_id:
      type: int
      aliases: ['os_id']
      description:
        - ID of the operating system to install.
        - Mutually exclusive with I(operating_system_name) and I(operating_system_regex).

    operating_system_name:
      type: str
      aliases: ['os_name']
      description:
        - Full name of the operating system to install (exact match on C(full_name)).
        - Mutually exclusive with I(operating_system_id) and I(operating_system_regex).

    operating_system_regex:
      type: str
      aliases: ['os_regex']
      description:
        - Regular expression to match an operating system by C(full_name) (case insensitive).
        - Must match exactly one OS option.
        - Mutually exclusive with I(operating_system_id) and I(operating_system_name).

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
- name: Create an SBM server using IDs
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: present
    location_id: 1
    flavor_id: 42
    hostname: my-sbm-server
    operating_system_id: 100
    wait: 86400
    update_interval: 60
  register: new_server

- name: Create an SBM server using human-readable names
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: present
    location_code: AMS7
    flavor_name: DL-01
    hostname: my-sbm-server
    os_name: 'Debian 13 64-bit'
  register: new_server

- name: Create an SBM server with OS regex
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: present
    location_code: AMS7
    flavor_name: DL-01
    hostname: my-sbm-server
    os_regex: 'Debian 13'
  register: new_server

- name: Delete an SBM server by ID (fire-and-forget)
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: absent
    server_id: '{{ server_id }}'

- name: Delete an SBM server by hostname
  serverscom.sc_api.sc_sbm_server:
    token: '{{ sc_token }}'
    state: absent
    hostname: my-sbm-server

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
    ScApi,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerCreate,
    ScSbmServerDelete,
    resolve_location_id,
    resolve_operating_system_id,
    resolve_sbm_flavor_model_id,
    resolve_sbm_server_id,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "required": True,
            },
            "server_id": {"type": "str"},
            "location_id": {"type": "int"},
            "location_code": {"type": "str"},
            "flavor_id": {"type": "int"},
            "flavor_name": {"type": "str"},
            "hostname": {"type": "str"},
            "operating_system_id": {
                "type": "int",
                "aliases": ["os_id"],
            },
            "operating_system_name": {
                "type": "str",
                "aliases": ["os_name"],
            },
            "operating_system_regex": {
                "type": "str",
                "aliases": ["os_regex"],
            },
            "ssh_key_fingerprints": {
                "type": "list",
                "elements": "str",
                "no_log": False,
            },
            "user_data": {"type": "str", "no_log": True},
            "wait": {"type": "int", "default": 86400},
            "update_interval": {"type": "int", "default": 60},
            "retry_on_conflicts": {"type": "bool", "default": True},
            "wait_for_deletion": {"type": "bool", "default": False},
        },
        required_if=[
            [
                "state",
                "present",
                ["hostname"],
            ],
            [
                "state",
                "present",
                ["location_id", "location_code"],
                True,
            ],
            [
                "state",
                "present",
                ["flavor_id", "flavor_name"],
                True,
            ],
            [
                "state",
                "present",
                [
                    "operating_system_id",
                    "operating_system_name",
                    "operating_system_regex",
                ],
                True,
            ],
            [
                "state",
                "absent",
                ["server_id", "hostname"],
                True,
            ],
        ],
        mutually_exclusive=[
            ["location_id", "location_code"],
            ["flavor_id", "flavor_name"],
            [
                "operating_system_id",
                "operating_system_name",
                "operating_system_regex",
            ],
            ["server_id", "location_id"],
            ["server_id", "location_code"],
        ],
        supports_check_mode=True,
    )
    try:
        if module.params["state"] == "present":
            api = ScApi(module.params["token"], module.params["endpoint"])
            location_id = resolve_location_id(
                api,
                location_id=module.params["location_id"],
                location_code=module.params["location_code"],
            )
            sbm_flavor_model_id = resolve_sbm_flavor_model_id(
                api,
                location_id,
                sbm_flavor_model_id=module.params["flavor_id"],
                sbm_flavor_model_name=module.params["flavor_name"],
            )
            operating_system_id = resolve_operating_system_id(
                api,
                location_id,
                sbm_flavor_model_id,
                operating_system_id=module.params["operating_system_id"],
                operating_system_name=module.params["operating_system_name"],
                operating_system_regex=module.params["operating_system_regex"],
            )
            instance = ScSbmServerCreate(
                endpoint=module.params["endpoint"],
                token=module.params["token"],
                location_id=location_id,
                sbm_flavor_model_id=sbm_flavor_model_id,
                hostname=module.params["hostname"],
                operating_system_id=operating_system_id,
                ssh_key_fingerprints=module.params.get("ssh_key_fingerprints"),
                user_data=module.params.get("user_data"),
                wait=module.params["wait"],
                update_interval=module.params["update_interval"],
                checkmode=module.check_mode,
            )
        elif module.params["state"] == "absent":
            api = ScApi(module.params["token"], module.params["endpoint"])
            server_id = resolve_sbm_server_id(
                api,
                server_id=module.params["server_id"],
                hostname=module.params["hostname"],
            )
            instance = ScSbmServerDelete(
                endpoint=module.params["endpoint"],
                token=module.params["token"],
                server_id=server_id,
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
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
