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
module: sc_baremetal_servers_info
version_added: "1.1.0"
author: "George Shuklin (@amarao)"
short_description: Information about existing dedicated servers
description: >
    Retrive list of all existing dedicated baremetal servers.

notes:
  - Not to be confused with M(serverscom.sc_api.sc_dedicated_servers_info).
  - Includes information for both dedicated and other types of servers
    (f.e. kubernetes baremetal node)

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
"""

RETURN = """
baremetal_servers:
  type: complex
  description:
   - List of servers
  contains:
    id:
      type: str
      description:
        - ID of the server
      returned: on success

    title:
      type: str
      description:
        - title of server (used as hostname).
      returned: on success

    type:
      type: str
      description:
        - always 'dedicated_server'
      returned: on success
  returned: on success
"""

EXAMPLES = """
- name: Get all servers
  sc_baremetal_servers_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
  register: srv_list

- name: Report server information
  debug:
    msg: '{{ item }}'
  loop: '{{ srv_list.baremetal_servers }}'
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScBaremetalServersInfo,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
        },
        supports_check_mode=True,
    )
    try:
        sc_baremetal_servers_info = ScBaremetalServersInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
        )
        module.exit_json(**sc_baremetal_servers_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
