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
module: sc_sbm_server_ptr_info
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Query PTR records for an SBM (Scalable Baremetal) server
description: >
    Returns the list of PTR records associated with
    IP addresses of the SBM (Scalable Baremetal) server.
extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    server_id:
      type: str
      description:
        - ID of the SBM server.
        - Mutually exclusive with I(hostname).

    hostname:
      type: str
      description:
        - Hostname of the SBM server (exact match on server title).
        - Mutually exclusive with I(server_id).
"""

RETURN = """
ptr_records:
  type: list
  description:
    - List of PTR records for the server.
  returned: on success
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

api_url:
  description: URL for the failed request.
  returned: on failure
  type: str

status_code:
  description: Status code for the request.
  returned: on failure
  type: int
"""

EXAMPLES = """
- name: Query PTR records by server ID
  serverscom.sc_api.sc_sbm_server_ptr_info:
    token: '{{ sc_token }}'
    server_id: abc123xyz
  register: ptr_info

- name: Query PTR records by hostname
  serverscom.sc_api.sc_sbm_server_ptr_info:
    token: '{{ sc_token }}'
    hostname: my-sbm-server
  register: ptr_info

- name: Show PTR records
  debug:
    var: ptr_info.ptr_records
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    ScApi,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerPtrInfo,
    resolve_sbm_server_id,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "token": {"type": "str", "no_log": True, "required": True},
            "server_id": {"type": "str"},
            "hostname": {"type": "str"},
        },
        required_one_of=[["server_id", "hostname"]],
        mutually_exclusive=[["server_id", "hostname"]],
        supports_check_mode=True,
    )
    try:
        api = ScApi(module.params["token"], module.params["endpoint"])
        server_id = resolve_sbm_server_id(
            api,
            server_id=module.params["server_id"],
            hostname=module.params["hostname"],
        )
        ptr_info = ScSbmServerPtrInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=server_id,
        )
        module.exit_json(**ptr_info.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
