#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2020, Servers.com
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
module: sc_cloud_computing_instance_ptr
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Manage cloud instances PTR records
description: >
    Add or remove PTR records to IP addresses of the instance.

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

    state:
      type: str
      required: true
      choices: ['present', 'absent', 'query']
      description:
        - State of the ptr record.
        - C(query) does not change anything and returns current list of PTRs
          for instance.

    name:
      type: str
      aliases: [instance_name]
      description:
        - Name of the instance to set PTR records for.
        - If more than one server with a given name found, module will fail.
        - Use I(instance_id) for precise identification.
        - Mutually exclusive with I(instance_id).

    instance_id:
      type: str
      description:
        - Id of the instance to manage PTR records for.
        - Mutually exclusive with I(name).

    region_id:
      type: int
      description:
        - Region ID to search instance by name.
        - All regions are searched if not specified.
        - Used only if I(name) present.

    ip:
      type: str
      default: all
      description:
        - IP address for PTR record.
        - IP address must belong to instance.
        - Reserved keyword C(all) can be used for automatically
          use all instance IP addresses.
        - Required for I(state)=C(present)

    domain:
      type: str
      description:
        - PTR domain name to accociate with IP address(es).
        - Required for I(state)=C(present).
        - I(ip) or I(domain) required for I(state)=C(absent).

    ttl:
      type: int
      description:
       - TTL (time to live) value for PTR caching.
       - Default API value C(60) is used if not specified.

    priority:
      type: int
      description:
        - Priority of the PTR record.
        - Default API value C(0) is used if not specified.
"""

RETURN = """
"""

EXAMPLES = """
- name: Add ptr record to all IP to instance by name
  sc_cloud_computing_instance_ptr:
    token: '{{ sc_token }}'
    name: myinstance
    domain: ptr.example.com
    state: present

- name: Add ptr record to IP 203.0.113.1 to instance by ID
  sc_cloud_computing_instance_ptr:
    token: '{{ sc_token }}'
    instance_id: M7e5Ba2v
    domain: ptr.example.org
    ip: 203.0.113.1
    ttl: 42
    priority: 42
    state: present

- name: Remove all PTRs for instance by name
  sc_cloud_computing_instance_ptr:
    token: '{{ sc_token }}'
    name: myinstance
    region_id: 2
    state: absent

- name: Remove PTRs for specific IP for instance
  sc_cloud_computing_instance_ptr:
    token: '{{ sc_token }}'
    instance_id: M7e5Ba2v
    ip: 198.51.100.42
    state: absent

- name: Remove PTRs for specific domain for instance
  sc_cloud_computing_instance_ptr:
    token: '{{ sc_token }}'
    instance_id: M7e5Ba2v
    domain: badptr.example.com
    state: absent
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
import json
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScCloudComputingInstancePtr,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "token": {"type": "str", "no_log": True, "required": True},
            "state": {
                "type": "str",
                "choices": ["present", "absent", "query"],
                "required": True,
            },
            "instance_id": {},
            "name": {"aliases": ["instance_name"]},
            "region_id": {"type": "int"},
            "ip": {"default": "all"},
            "domain": {},
            "ttl": {"type": "int"},
            "priority": {"type": "int"},
        },
        mutually_exclusive=[["name", "instance_id"]],
        required_if=[["state", "present", ["domain"]]],
        supports_check_mode=True,
    )
    try:
        ptr = ScCloudComputingInstancePtr(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            state=module.params["state"],
            instance_id=module.params["instance_id"],
            name=module.params["name"],
            region_id=module.params["region_id"],
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
