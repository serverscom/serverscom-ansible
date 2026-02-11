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
module: sc_sbm_server_info
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Information about existing SBM (Scalable Baremetal) server
description: >
    Retrieve information about existing Scalable Baremetal server.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
    server_id:
      type: str
      description:
        - ID of the SBM server.
        - Mutually exclusive with I(hostname).
        - If ID is malformed, error 400 is returned.

    hostname:
      type: str
      description:
        - Hostname of the SBM server (exact match on server title).
        - Mutually exclusive with I(server_id).

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
    - Always 'sbm_server'.
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
    - "provisioning: activation after order."
    - "installation: OS reinstall in progress."
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
  type: int
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
    sbm_flavor_model_id:
      type: int
      description:
        - Unique identifier of the SBM flavor model.
        - May be absent.
    sbm_flavor_model_name:
      type: str
      description:
        - Human-readable name of the SBM flavor model.
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
    - True if server exists; false if absent and fail_on_absent is false.
  returned: on success

ready:
  type: bool
  description:
    - "Synthetic: true if I(status)=Q(active), I(power_status)=Q(powered_on), I(operational_status)=Q(normal)."
  returned: on success
"""  # noqa

EXAMPLES = """
- name: Get SBM server info by ID
  serverscom.sc_api.sc_sbm_server_info:
    token: "{{ sc_token }}"
    server_id: 'abc123xyz'
  register: srv

- name: Get SBM server info by hostname
  serverscom.sc_api.sc_sbm_server_info:
    token: "{{ sc_token }}"
    hostname: my-sbm-server
  register: srv

- name: Report server information
  debug:
    msg: 'Server {{ srv.title }} has IP {{ srv.public_ipv4_address }}'

- name: Wait until SBM server is ready
  serverscom.sc_api.sc_sbm_server_info:
    token: "{{ sc_token }}"
    server_id: 'abc123xyz'
  register: srv
  until: srv.ready
  delay: 30
  retries: 60
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    ScApi,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerInfo,
    resolve_sbm_server_id,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "server_id": {"type": "str"},
            "hostname": {"type": "str"},
            "fail_on_absent": {"type": "bool", "default": True},
        },
        required_one_of=[["server_id", "hostname"]],
        mutually_exclusive=[["server_id", "hostname"]],
        supports_check_mode=True,
    )
    try:
        api = ScApi(module.params["token"], module.params["endpoint"])
        try:
            server_id = resolve_sbm_server_id(
                api,
                server_id=module.params["server_id"],
                hostname=module.params["hostname"],
            )
        except ModuleError:
            if module.params["hostname"] and not module.params["fail_on_absent"]:
                module.exit_json(changed=False, found=False, ready=False)
            raise
        sc_sbm_server_info = ScSbmServerInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=server_id,
            fail_on_absent=module.params["fail_on_absent"],
        )
        module.exit_json(**sc_sbm_server_info.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
