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

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    type:
      type: str
      choices: ["dedicated_server", "kubernetes_baremetal_node", "sbm_server"]
      description:
        - Type of server to filter.
        - One of "dedicated_server", "kubernetes_baremetal_node", "sbm_server".
        - If not specified, all servers will be returned.

    search_pattern:
        type: str
        description:
            - Search for substring in locations names.
            - Case insensitive.

    label_selector:
        type: str
        description:
            - Search for bare metal servers with specific labels.
            - More info at https://developers.servers.com/api-documentation/v1/#section/Labels/Labels-selector
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

    rack_id:
      type: str
      description:
        - ID of the rack where server is located.
      returned: on success

    status:
      type: str
      description:
        - Status of the server.
        - One of "init" - host is ordered but not provisioned yet,
          "pending" - there is an operation in progress on a host,
          "active" - host is ready to use.
      returned: on success

    operational_status:
      type: str
      description:
        - Provides more details on executed operations.
        - Might be one of "normal" - there are no operations on a host, but this status doesn't guarantee that a host is accessible by SSH;
          "provisioning" - a host is being activated after ordering;
          "installation" - this status is displayed while OS reinstalling;
          "entering_rescue_mode", "rescue_mode", "exiting_rescue_mode" - these statuses show rescue mode process.
      returned: on success

    type:
      type: str
      description:
        - One of "dedicated_server", "kubernetes_baremetal_node", "sbm_server", depending on the type of server.
      returned: on success

    power_status:
      type: str
      description:
        - Power status of the server.
        - One of "unknown" - this status is displayed while provisioning or in a case when something went wrong;
          "powering_on" - transition status between power off and on;
          "powered_on" - power is on;
          "powering_off" - transition status between power on and off;
          "powered_off" - power is off;
          "power_cycling" - power reboot.
      returned: on success

    configuration:
      type: str
      description:
        - Configuration contains information about a chassis model, RAM, and disk drives.
      returned: on success

    location_id:
      type: int
      description:
        - Unique identifier of a location where a host is deployed.
      returned: on success

    location_code:
      type: str
      description:
        - Technical title of a location.
      returned: on success

    private_ipv4_address:
      type: str
      description:
        - An IPv4 address assigned to a host for a private network.
        - May be null if no private network is connected to a host.
      returned: on success

    public_ipv4_address:
      type: str
      description:
        - An IPv4 address assigned to a host for a public network.
        - May be null if no public network is connected to a host.
      returned: on success

    oob_ipv4_address:
      type: str
      description:
        - OOB IPv4 address.
        - May be null if OOB access is not enabled.
      returned: on success

    lease_start_at:
      type: str
      description:
        - The date when leasing of a host has been started.
        - May be null if a host is not leased.
      returned: on success

    scheduled_release_at:
      type: str
      description:
        - A scheduled date and time when a host will be released.
        - May be null if a host is not leased.
      returned: on success

    labels:
      type: dict
      description:
        - Labels associated with a resource. Refer to the Labels section for more details.
      returned: on success

    created_at:
      type: str
      description:
        - A date and time when a host was created.
      returned: on success

    updated_at:
      type: str
      description:
        - A date and time of the host's last update.
      returned: on success
  returned: on success
"""

EXAMPLES = """
- name: Get all servers
  sc_baremetal_servers_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    search_pattern: "some-host-"
    label_selector: "environment==staging"
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
            "type": {
                "type": "str",
                "choices": [
                    "dedicated_server",
                    "kubernetes_baremetal_node",
                    "sbm_server",
                ],
            },
            "search_pattern": {"type": "str"},
            "label_selector": {"type": "str"},
        },
        supports_check_mode=True,
    )
    try:
        sc_baremetal_servers_info = ScBaremetalServersInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            type=module.params.get("type"),
            search_pattern=module.params.get("search_pattern"),
            label_selector=module.params.get("label_selector"),
        )
        module.exit_json(**sc_baremetal_servers_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
