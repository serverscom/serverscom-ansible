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
module: sc_sbm_os_list
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Return available operating system options for SBM servers.
description: >
    Return list of OS images for Scalable Baremetal (SBM) servers
    in a specified location and flavor model.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
    location_id:
      type: int
      required: true
      description:
        - Location identifier.
    sbm_flavor_model_id:
      type: str
      description:
        - A unique identifier of an SBM flavor.
        - Mutually exclusive with I(sbm_flavor_model_name).
    sbm_flavor_model_name:
      type: str
      description:
        - Human-readable name of an SBM flavor (mutually exclusive with I(sbm_flavor_model_id)).
        - If set the module will resolve the name to an ID and return OS options for that model.
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
- name: List OS options by location_id and sbm_flavor_model_id
  serverscom.sc_api.sc_sbm_os_list:
    token: "{{ api_token }}"
    location_id: "32"
    sbm_flavor_model_id: "1287"
  register: result

- name: List OS options by location and SBM model name
  serverscom.sc_api.sc_sbm_os_list:
    token: "{{ api_token }}"
    location_id: "32"
    sbm_flavor_model_name: "DL-01"
  register: result

- name: List OS options with name filter
  serverscom.sc_api.sc_sbm_os_list:
    token: "{{ api_token }}"
    location_id: "32"
    sbm_flavor_model_id: "1287"
    os_name_regex: "Ubuntu"
  register: result

- debug:
    var: result.os_list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmOSList,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "location_id": {"type": "int", "required": True},
            "sbm_flavor_model_id": {"type": "str"},
            "sbm_flavor_model_name": {"type": "str"},
            "os_name_regex": {"type": "str"},
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ["sbm_flavor_model_id", "sbm_flavor_model_name"],
        ],
        required_one_of=[
            ["sbm_flavor_model_id", "sbm_flavor_model_name"],
        ],
    )
    try:
        sc_os = ScSbmOSList(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            location_id=module.params["location_id"],
            sbm_flavor_model_id=module.params.get("sbm_flavor_model_id"),
            sbm_flavor_model_name=module.params.get("sbm_flavor_model_name"),
            os_name_regex=module.params.get("os_name_regex"),
        )
        module.exit_json(**sc_os.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
