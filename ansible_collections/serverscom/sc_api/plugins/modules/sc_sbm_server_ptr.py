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
author: "Vil Surkin (@vills)"
short_description: Manage SBM server PTR records
description: >
    Add or remove PTR records to IP addresses of the SBM (Scalable Baremetal) server.

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
      type: str
      required: true
      description:
        - ID of the SBM server to manage PTR records for.

    state:
      type: str
      required: true
      choices: ['present', 'absent', 'query']
      description:
        - State of the PTR record.
        - C(query) does not change anything and returns current list of PTRs
          for the server.
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
- name: Query current PTR records
  serverscom.sc_api.sc_sbm_server_ptr:
    token: '{{ sc_token }}'
    server_id: abc123xyz
    state: query
  register: ptr_info

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
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerPtr,
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
                "choices": ["present", "absent", "query"],
                "required": True,
            },
            "ip": {"type": "str"},
            "domain": {"type": "str"},
            "ttl": {"type": "int"},
            "priority": {"type": "int"},
        },
        required_if=[["state", "present", ["domain", "ip"]]],
        supports_check_mode=True,
    )
    try:
        ptr = ScSbmServerPtr(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            state=module.params["state"],
            server_id=module.params["server_id"],
            ip=module.params["ip"],
            domain=module.params["domain"],
            ttl=module.params["ttl"],
            priority=module.params["priority"],
            checkmode=module.check_mode,
        )
        module.exit_json(**ptr.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
