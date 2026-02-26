#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2025, Servers.com
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
module: sc_baremetal_os_list
version_added: "1.0.0"
author: "Volodymyr Rudniev (@koef)"
short_description: Return available operating system options.
description: >
    Return list of OS images for bare metal dedicated servers in a specified location.
    For SBM (Scalable Baremetal) servers, use M(serverscom.sc_api.sc_sbm_os_list) instead.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    server_id:
      type: str
      description:
        - A unique identifier of the bare metal server.
        - If specified the module will return OS options for the specified server.
        - If set the parameters I(location_id), I(location_code), I(server_model_id), and I(server_model_name) will be ignored.
    location_id:
      type: str
      description:
        - Location identifier.
    location_code:
      type: str
      description:
        - Human-readable location slug (mutually exclusive with I(location_id)).
    server_model_id:
      type: str
      description:
        - Server model identifier (mutually exclusive with I(server_model_name)).
    server_model_name:
      type: str
      description:
        - Server model name (mutually exclusive with I(server_model_id)).
    os_name_regex:
      type: str
      description:
        - A regular expression to filter OS options by name.
        - If specified, the module will return only OS options that match the provided regex.
"""

RETURN = """
os_list:
  type: list
  elements: dict
  returned: on success
  description:
    - List of operating system options.
  contains:
    id:
      type: str
      description: A unique identifier of an operating system.
    full_name:
      type: str
      description: This parameter contains a name, version, and architecture of an operating system.
    name:
      type: str
      description: A human-readable name of an operating system.
    version:
      type: str
      description: A version of an operating system.
    arch:
      type: str
      description: Architecture of an operating system.
    filesystems:
      type: list
      description: This parameter contains a list of available file systems for an operating system.

api_url:
  type: str
  returned: on failure
  description:
    - Failed request URL.
status_code:
  type: int
  returned: always
  description:
    - HTTP status code.
"""

EXAMPLES = """
    - name: List OS options by location_id and server_model_id
      sc_baremetal_os_list:
        token: "{{ api_token }}"
        location_id: "34"
        server_model_id: "12345"
      register: result

    - name: List OS options by location_code and server_model_name
      sc_baremetal_os_list:
        token: "{{ api_token }}"
        location_code: "ams1"
        server_model_name: "R430"
      register: result

    - debug:
        var: result.os_list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScDedicatedOSList,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "server_id": {"type": "str"},
            "location_id": {"type": "str"},
            "location_code": {"type": "str"},
            "server_model_id": {"type": "str"},
            "server_model_name": {"type": "str"},
            "os_name_regex": {"type": "str"},
        },
        supports_check_mode=True,
        required_one_of=[["server_id", "location_id", "location_code"]],
        mutually_exclusive=[
            ["server_id", "location_id", "location_code"],
            ["server_model_id", "server_model_name"],
        ],
        required_if=[
            [
                "location_id",
                "present",
                ("server_model_id", "server_model_name"),
                True,
            ],
            [
                "location_code",
                "present",
                ("server_model_id", "server_model_name"),
                True,
            ],
        ],
    )
    try:
        sc_os = ScDedicatedOSList(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params.get("server_id"),
            location_id=module.params.get("location_id"),
            location_code=module.params.get("location_code"),
            server_model_id=module.params.get("server_model_id"),
            server_model_name=module.params.get("server_model_name"),
            os_name_regex=module.params.get("os_name_regex"),
        )
        module.exit_json(**sc_os.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
