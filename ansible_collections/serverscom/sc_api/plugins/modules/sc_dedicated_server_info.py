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
module: sc_dedicated_server_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Information about existing dedicated server
description: >
    Retrive information about existing dedicated baremetal server.

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

    name:
      aliases: [id]
      type: str
      required: true
      description:
        - ID of the server.
        - Translates to server_id in API.
        - If ID is malformed, error 400 is returned.

    fail_on_absent:
      type: bool
      default: true
      description:
        - Raise error if server is not found.
        - If set to false, absent (not found) server will have
          found=false in server info.
"""

RETURN = """
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

rack_id:
  type: str
  description:
    - ID of rack where server is installed.
    - May be null if not supported.
  returned: on success

status:
  type: str
  description:
    - Status of server.
    - Values "init" and "pending" are transient.
    - Value "active" is a normal status for a server.
  returned: on success

operational_status:
  type: str
  description:
    - Maintanance operations for the server.
    - Value 'normal' is used for the server without any operations.
    - Value 'provisioning' is used for the server under provisioning.
    - Value 'installation' is used for reinstalled/installed server
      during OS installation process.
    - Value 'entering_rescue_mode' is used during reconfiguration of the server
      for the rescue mode.
    - Value 'exiting_rescue_mode' is used during reconfiguration of the server
      from rescue mode to normal.
    - Value 'rescue_mode' is used for server in rescue mode.
  returned: on success

power_status:
    type: str
    description:
      - Power state of the server.
      - Possible values are unknown, powering_on, powering_off, powered_off,
        powered_on (normal mode for working server), power_cycling (sequence of
        off on operations).
    returned: on success

configuration:
  type: str
  description:
      - Server configuration
  returned: on success

location_id:
  type: str
  description:
    - ID of the location of the server.
  returned: on success

location_code:
  type: str
  description:
    - Code for location of the server.
  returned: on success

private_ipv4_address:
  type: str
  description:
     - IPv4 address of the server on the private network.
     - May be absent.
  returned: on success

public_ipv4_address:
  type: str
  description:
     - IPv4 address of the server on the public (internet) network.
     - May be absent.
  returned: on success

lease_start_at:
  type: str
  description:
     - Date when server lease started.
     - May be absent.
  returned: on success

scheduled_release_at:
   type: str
   description:
      - Date when server lease is planned for termination.
      - May be absent.
   returned: on success

configuration_details:
   type: complex
   description:
     - Structured server configuration
   contains:
     ram_size:
       type: int
       description:
         - server RAM.
         - May be absent.
     server_model_id:
       type: str
       description:
         - Internal ID of the server model.
         - May be absent.
     bandwidth_id:
       type: str
       description:
         - ID of the bandwidth accounting item associated with server.
         - May be absent.
     bandwidth_name:
       type: str
       description:
          - Name of the bandwidth accounting item associated with server.
          - May be absent.
     private_uplink_id:
       type: str
       description:
         - ID of the server uplink in the private network.
         - May be absent.
     private_uplink_name:
       type: str
       description:
         - Name of the server uplink in the private network.
         - May be absent.
     public_uplink_id:
       type: str
       description:
         - ID of the server uplink in the public network.
         - May be absent.
     public_uplink_name:
       type: str
       description:
         - Name of the server uplink in the public network.
         - May be absent.
     operating_system_id:
       type: str
       description:
         - ID of the installed OS on the server.
         - May be absent.
     operating_system_full_name:
       type: str
       description:
         - Name of the installed OS on the server.
         - May be absent.
   returned: on success

created_at:
  type: str
  description:
    - Date the server object was created in database.
  returned: on success

updated_at:
  type: str
  description:
    - Last date when the server object was updated.
  returned: on success

found:
  type: bool
  description:
    - Set to true if server is found.
    - Set to false if server is not found and I(can_be_absent)=C(true)
  returned: on success

ready:
  type: bool
  description:
    - Synthetic attribute, created by module.
    - Set to true if server is in status=active, power_status=powered_on,
      operational_status=normal.
  returned: on success
"""

EXAMPLES = """
- name: Get server info
  sc_dedicated_server_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    id: '0m592Zmn'
  register: srv
- name: Report server information
  debug:
    msg: 'Server {{ srv.name }} has IP {{ srv.public_ipv4_address }}'

- name: Wait until server is ready
  sc_dedicated_server_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    id: '0m592Zmn'
  register: srv
  until: srv.ready
  delay: 30
  retries: 300
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
import json
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScDedicatedServerInfo,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "name": {"type": "str", "required": True, "aliases": ["id"]},
            "fail_on_absent": {"type": "bool", "default": True},
        },
        supports_check_mode=True,
    )
    try:
        sc_dedicated_server_info = ScDedicatedServerInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            name=module.params["name"],
            fail_on_absent=module.params["fail_on_absent"],
        )
        module.exit_json(**sc_dedicated_server_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
