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
    - Unique identifier of the server.
  returned: on success

title:
  type: str
  description:
    - Displayed name of the server.
  returned: on success

type:
  type: str
  description:
    - Always 'dedicated_server'.
  returned: on success

rack_id:
  type: str
  description:
    - Unique identifier of the rack where the server is deployed.
    - May be null on provisioning stage.
  returned: on success

status:
  type: str
  description:
    - "State of the server."
    - "init, pending: transitional."
    - "active: ready-to-use."
  returned: on success

operational_status:
  type: str
  description:
    - Maintenance operation status.
    - "normal: no operations (doesn't guarantee SSH access)."
    - "maintenance: scheduled maintenance."
    - "provisioning: activation after order."
    - "installation: OS reinstall in progress."
    - "entering_rescue_mode: switching to rescue mode."
    - "rescue_mode: in rescue mode."
    - "exiting_rescue_mode: restoring to normal."
  returned: on success

power_status:
  type: str
  description:
    - "unknown: during provisioning or on error."
    - "powering_on/powering_off: transitional."
    - "powered_on: on."
    - "powered_off: off."
    - "power_cycling: reboot sequence."
  returned: on success

configuration:
  type: str
  description:
    - Information about chassis model, RAM, and disk drives.
  returned: on success

location_id:
  type: str
  description:
    - Unique identifier of the server's location.
  returned: on success

location_code:
  type: str
  description:
    - Technical code of the server's location.
  returned: on success

private_ipv4_address:
  type: str
  description:
    - IPv4 address on the private network.
    - May be null.
  returned: on success

public_ipv4_address:
  type: str
  description:
    - IPv4 address on the public network.
    - May be null.
  returned: on success

oob_ipv4_address:
  type: str
  description:
    - Out-of-band IPv4 address when OOB access is enabled.
    - May be null.
  returned: on success

lease_start_at:
  type: str
  description:
    - Date when server lease started.
    - May be null.
  returned: on success

scheduled_release_at:
  type: str
  description:
    - Scheduled date and time for server release.
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
        - RAM size.
        - May be absent.
    server_model_id:
      type: int
      description:
        - Unique identifier of the server model.
        - May be absent.
    server_model_name:
      type: str
      description:
        - Human-readable name of the server model.
        - May be absent.
    bandwidth_id:
      type: int
      description:
        - Unique identifier of the bandwidth option.
        - May be absent.
    bandwidth_name:
      type: str
      description:
        - Human-readable name of the bandwidth option.
        - May be absent.
    private_uplink_id:
      type: int
      description:
        - Unique identifier of the private uplink option.
        - May be absent.
    private_uplink_name:
      type: str
      description:
        - Human-readable name of the private uplink option.
        - May be absent.
    public_uplink_id:
      type: int
      description:
        - Unique identifier of the public uplink option.
        - May be absent.
    public_uplink_name:
      type: str
      description:
        - Human-readable name of the public uplink option.
        - May be absent.
    operating_system_id:
      type: int
      description:
        - Unique identifier of the installed OS.
        - May be absent.
    operating_system_full_name:
      type: str
      description:
        - Human-readable name of the installed OS.
        - May be absent.
  returned: on success

labels:
  type: dict
  description:
    - Labels associated with the server.
  returned: on success

created_at:
  type: str
  description:
    - Date and time when the server was created.
  returned: on success

updated_at:
  type: str
  description:
    - Date and time of the server's last update.
  returned: on success

found:
  type: bool
  description:
    - True if server exists; false if absent and can_be_absent is true.
  returned: on success

ready:
  type: bool
  description:
    - "Synthetic: true if I(status)=Q(active), I(power_status)=Q(powered_on), I(operational_status)=Q(normal)."
  returned: on success
"""  # noqa

EXAMPLES = """
- name: Get server info
  serverscom.sc_api.sc_dedicated_server_info:
    token: "<your_token>"
    id: '0m592Zmn'
  register: srv
- name: Report server information
  debug:
    msg: 'Server {{ srv.name }} has IP {{ srv.public_ipv4_address }}'

- name: Wait until server is ready
  serverscom.sc_api.sc_dedicated_server_info:
    token: "<your_token>"
    id: '0m592Zmn'
  register: srv
  until: srv.ready
  delay: 30
  retries: 300
"""

from ansible.module_utils.basic import AnsibleModule
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
