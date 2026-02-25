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
module: sc_sbm_server_ptr
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Manage SBM server PTR records
description: >
    Add or remove PTR records for IP addresses of the SBM (Scalable Baremetal) server.
    Use M(serverscom.sc_api.sc_sbm_server_ptr_info) to query existing PTR records.
extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    server_id:
      type: str
      description:
        - ID of the SBM server to manage PTR records for.
        - Mutually exclusive with I(hostname).

    hostname:
      type: str
      description:
        - Hostname of the SBM server (exact match on server title).
        - Mutually exclusive with I(server_id).

    state:
      type: str
      required: true
      choices: ['present', 'absent']
      description:
        - State of the PTR record.
        - C(present) creates the PTR record if it doesn't exist.
        - C(absent) removes matching PTR records.

    ip:
      type: str
      description:
        - IP address for PTR record.
        - IP address must belong to the server.
        - Required for I(state)=C(present).
        - I(ip) or I(domain) required for I(state)=C(absent).

    domain:
      type: str
      description:
        - PTR domain name to associate with IP address.
        - Required for I(state)=C(present).
        - I(ip) or I(domain) required for I(state)=C(absent).

    ttl:
      type: int
      description:
       - TTL (time to live) value for PTR caching in seconds.
       - Default API value C(60) is used if not specified.

    priority:
      type: int
      description:
        - Priority of the PTR record.
        - Default API value C(0) is used if not specified.
"""

RETURN = """
ptr_records:
  type: list
  description:
    - List of PTR records for the server.
  returned: always
  contains:
    id:
      type: str
      description:
        - Unique identifier of the PTR record.
    ip:
      type: str
      description:
        - IP address of the PTR record.
    domain:
      type: str
      description:
        - Domain name of the PTR record.
    ttl:
      type: int
      description:
        - TTL value of the PTR record.
    priority:
      type: int
      description:
        - Priority of the PTR record.
"""

EXAMPLES = """
- name: Add PTR record to server
  serverscom.sc_api.sc_sbm_server_ptr:
    token: '{{ sc_token }}'
    server_id: abc123xyz
    domain: server.example.com
    ip: 203.0.113.1
    state: present

- name: Add PTR record with custom TTL
  serverscom.sc_api.sc_sbm_server_ptr:
    token: '{{ sc_token }}'
    server_id: abc123xyz
    domain: server.example.org
    ip: 203.0.113.2
    ttl: 300
    priority: 10
    state: present

- name: Remove PTR record by IP
  serverscom.sc_api.sc_sbm_server_ptr:
    token: '{{ sc_token }}'
    server_id: abc123xyz
    ip: 198.51.100.42
    state: absent

- name: Remove PTR record by domain
  serverscom.sc_api.sc_sbm_server_ptr:
    token: '{{ sc_token }}'
    server_id: abc123xyz
    domain: old.example.com
    state: absent
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    ScApi,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerPtr,
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
                "choices": ["present", "absent"],
                "required": True,
            },
            "ip": {"type": "str"},
            "domain": {"type": "str"},
            "ttl": {"type": "int"},
            "priority": {"type": "int"},
        },
        required_one_of=[["server_id", "hostname"]],
        mutually_exclusive=[["server_id", "hostname"]],
        required_if=[
            ["state", "present", ["domain", "ip"]],
            ["state", "absent", ["ip", "domain"], True],
        ],
        supports_check_mode=True,
    )
    try:
        api = ScApi(module.params["token"], module.params["endpoint"])
        server_id = resolve_sbm_server_id(
            api,
            server_id=module.params["server_id"],
            hostname=module.params["hostname"],
        )
        ptr = ScSbmServerPtr(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            state=module.params["state"],
            server_id=server_id,
            ip=module.params["ip"],
            domain=module.params["domain"],
            ttl=module.params["ttl"],
            priority=module.params["priority"],
            checkmode=module.check_mode,
        )
        module.exit_json(**ptr.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
