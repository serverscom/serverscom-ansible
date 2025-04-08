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
module: sc_load_balancer_instance_l4
version_added: "1.0.0"
author: "Volodymyr Rudniev (@koef)"
short_description: Create, update, or delete L4 load balancer instances via Servers.com Public API
description:
  - This module manages L4 load balancer instances.
  - It supports creating, updating, and deleting load balancer instances.
notes:
  - For creation (state "present" without providing an "id"), "name", "location_id", "vhost_zones", and "upstream_zones" are required.
  - For update (state "present" with an "id" or when identifying an existing object by "name"), provide either "id" or "name" (but not both) along with parameters to modify.
  - For deletion (state "absent"), provide exactly one of "id" or "name".
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
      - You can create token for your account in https://portal.servers.com
        in Profile -> Public API section.
  state:
    description: Define the desired state of the load balancer instance.
    required: true
    type: str
    choices: ["present", "absent"]
  wait:
    description:
      - "Maximum time in seconds to wait for the load balancer instance to reach the desired state after an action (e.g. deletion)."
      - "Default value is 600 seconds."
    required: false
    type: int
    default: 600
  update_interval:
    description:
      - "Interval in seconds between consecutive status checks during state transitions."
      - "Default value is 5 seconds."
    required: false
    type: int
    default: 5
  id:
    description:
      - "Unique identifier of the load balancer."
      - "For state 'present' (update), provide either 'id' or 'name' but not both."
      - "For state 'absent', provide exactly one of 'id' or 'name'."
    required: false
    type: str
  name:
    description:
      - "Name for the load balancer."
      - "For creation (state 'present' without an 'id'), required."
      - "For update, provide either 'id' or 'name' (but not both)."
    required: false
    type: str
  location_id:
    description: "Location ID where the load balancer will be created. (Required for creation)"
    required: false
    type: int
  cluster_id:
    description: >
      Unique identifier of a dedicated Load Balancer cluster.
      If omitted, a shared cluster is used.
    required: false
    type: str
  store_logs:
    description: "Enable log storage. Default is false."
    required: false
    type: bool
    default: false
  store_logs_region_id:
    description: "Cloud region ID for log storage."
    required: false
    type: int
  new_external_ips_count:
    description: "Number of new external IP addresses (update only)."
    required: false
    type: int
  delete_external_ips:
    description: "List of external IP addresses to delete (update only)."
    required: false
    type: list
    elements: str
  shared_cluster:
    description: "If true, the load balancer will move to a shared cluster (update only)."
    required: false
    type: bool
    default: true
  vhost_zones:
    description: "List of vhost zone objects defining forwarding rules."
    required: true
    type: list
    elements: dict
    suboptions:
      id:
        description: "Unique identifier of a zone. (1 to 255 characters)"
        required: true
        type: str
      ports:
        description: "Array of port numbers to apply the rule."
        required: true
        type: list
        elements: int
      udp:
        description: "Enable UDP traffic balancing. Default is false."
        required: false
        type: bool
        default: false
      proxy_protocol:
        description: "Enable proxy protocol. Default is false."
        required: false
        type: bool
        default: false
      upstream_id:
        description: "Unique identifier of an upstream server."
        required: true
        type: str
      description:
        description: "Optional comment (max 255 characters)."
        required: false
        type: str
  upstream_zones:
    description: "List of upstream zone objects grouping upstream servers."
    required: true
    type: list
    elements: dict
    suboptions:
      id:
        description: "Unique identifier of a zone. (1 to 255 characters)"
        required: true
        type: str
      method:
        description: >
          Traffic distribution method.
          Options: "random.least_conn", "round-robin", "least_conn". Default is "random.least_conn".
        required: false
        type: str
        choices: ["random.least_conn", "round-robin", "least_conn"]
        default: "random.least_conn"
      udp:
        description: "Enable UDP traffic balancing. Default is false."
        required: false
        type: bool
        default: false
      hc_interval:
        description: "Health check interval in seconds. Range: 1 to 60. Default is 5."
        required: false
        type: int
        default: 5
      hc_jitter:
        description: "Health check jitter in seconds. Range: 0 to 60. Default is 5."
        required: false
        type: int
        default: 5
      upstreams:
        description: "List of upstream server objects."
        required: true
        type: list
        elements: dict
        suboptions:
          ip:
            description: "IP address of the upstream server."
            required: true
            type: str
          port:
            description: "Port number of the upstream server."
            required: true
            type: int
          weight:
            description: "Traffic weight. Default is 1."
            required: false
            type: int
            default: 1
          max_conns:
            description: "Maximum connections per upstream. Range: 1 to 65535. Default is 63000."
            required: false
            type: int
            default: 63000
          max_fails:
            description: "Allowed failures before marking as unhealthy. Default is 0."
            required: false
            type: int
            default: 0
          fail_timeout:
            description: "Health check timeout in seconds. Range: 1 to 60. Default is 30."
            required: false
            type: int
            default: 30
  labels:
    description: "Dictionary of labels to attach to the load balancer."
    required: false
    type: dict
"""

RETURN = """
---
# When state is "present" (create) or "update", the module returns a dictionary with the following keys:
id:
  description: "Load Balancer instance ID."
  returned: always
  type: str
type:
  description: "Type of load balancer instance. Always 'l4'."
  returned: always
  type: str
name:
  description: "Human-readable name of the load balancer."
  returned: always
  type: str
location_id:
  description: "Location ID of the load balancer."
  returned: always
  type: int
cluster_id:
  description: "Dedicated cluster ID if applicable; null when on a shared cluster."
  returned: always
  type: str
shared_cluster:
  description: "Boolean indicating if the load balancer is hosted on a shared cluster."
  returned: always
  type: bool
store_logs:
  description: "Indicator whether log storage is enabled."
  returned: always
  type: bool
store_logs_region_id:
  description: "Cloud region ID for log storage."
  returned: always
  type: int
external_addresses:
  description: "List of external IPv4 addresses assigned to the load balancer."
  returned: always
  type: list
  elements: str
labels:
  description: "Labels attached to the load balancer."
  returned: always
  type: dict
created_at:
  description: "Timestamp when the load balancer was created."
  returned: always
  type: str
updated_at:
  description: "Timestamp when the load balancer was last updated."
  returned: always
  type: str
status:
  description: "Current status of the load balancer instance."
  returned: always
  type: str
  sample: "active"
vhost_zones:
  description: "List of vhost zone objects defining forwarding rules."
  returned: always
  type: list
  elements: dict
  suboptions:
    id:
      description: "Unique identifier of the vhost zone."
      returned: always
      type: str
    upstream_id:
      description: "Identifier of the associated upstream zone."
      returned: always
      type: str
    ports:
      description: "List of port numbers applied to the rule."
      returned: always
      type: list
      elements: int
    udp:
      description: "Indicates if UDP traffic balancing is enabled."
      returned: always
      type: bool
    proxy_protocol:
      description: "Indicates if the proxy protocol is enabled."
      returned: always
      type: bool
    acl_allow:
      description: "Flag indicating if ACL rules are applied."
      returned: always
      type: bool
    acl_list:
      description: "List of ACL rules."
      returned: always
      type: list
      elements: str
    description:
      description: "Optional comment for the vhost zone."
      returned: always
      type: str
upstream_zones:
  description: "List of upstream zone objects grouping upstream servers."
  returned: always
  type: list
  elements: dict
  suboptions:
    id:
      description: "Unique identifier of the upstream zone."
      returned: always
      type: str
    hc_interval:
      description: "Health check interval in seconds."
      returned: always
      type: int
    hc_jitter:
      description: "Health check jitter in seconds."
      returned: always
      type: int
    hc_fails:
      description: "Number of failed checks before an upstream is removed from load balancing."
      returned: always
      type: int
    hc_passes:
      description: "Number of successful checks to reinstate an upstream."
      returned: always
      type: int
    method:
      description: "Load balancing method."
      returned: always
      type: str
      sample: "random.least_conn"
    udp:
      description: "Indicates if UDP traffic balancing is enabled for the upstream zone."
      returned: always
      type: bool
    upstreams:
      description: "List of upstream server objects."
      returned: always
      type: list
      elements: dict
      suboptions:
        ip:
          description: "IPv4 address of the upstream server."
          returned: always
          type: str
        port:
          description: "Port of the upstream server."
          returned: always
          type: int
        weight:
          description: "Traffic weight for the upstream server."
          returned: always
          type: int
        max_fails:
          description: "Maximum allowed failures before the server is considered unhealthy."
          returned: always
          type: int
        fail_timeout:
          description: "Timeout in seconds to consider a health check as failed."
          returned: always
          type: int
        max_conns:
          description: "Maximum number of connections allowed for the upstream server."
          returned: always
          type: int
        status:
          description: "Current health status of the upstream server."
          returned: always
          type: str
          sample: "online"

# When state is "absent", no return value is provided.
"""

EXAMPLES = """
# Create or update an L4 load balancer instance
- name: Create L4 load balancer instance
  serverscom.sc_api.sc_load_balancer_instance_l4:
    token: "your-api-token"
    state: present
    name: "my-load-balancer"
    location_id: 1
    cluster_id: W0gXjnqr
    store_logs: true
    store_logs_region_id: 2
    vhost_zones:
      - id: "zone1"
        ports: [80, 443]
        udp: false
        proxy_protocol: false
        upstream_id: "upstream-group-1"
        description: "Vhost zone for web traffic"
    upstream_zones:
      - id: "upstream-zone1"
        method: "random.least_conn"
        udp: false
        hc_interval: 5
        hc_jitter: 5
        upstreams:
          - ip: "192.168.1.10"
            port: 8080
            weight: 1
            max_conns: 63000
            max_fails: 0
            fail_timeout: 30
    labels:
      environment: production
  register: lb_create

# Delete an L4 load balancer instance by name
- name: Delete L4 load balancer instance
  serverscom.sc_api.sc_load_balancer_instance_l4:
    token: "your-api-token"
    state: absent
    name: "lb-instance-name"

# Delete an L4 load balancer instance by id
- name: Delete L4 load balancer instance
  serverscom.sc_api.sc_load_balancer_instance_l4:
    token: "your-api-token"
    state: absent
    id: "lb-instance-id"
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScLbInstanceL4CreateUpdate,
    ScLbInstanceDelete,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"no_log": True, "required": True, "type": "str"},
            "endpoint": {"default": DEFAULT_API_ENDPOINT, "type": "str"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "required": True,
            },
            "id": {"type": "str"},
            "name": {"type": "str"},
            "location_id": {"type": "int"},
            "cluster_id": {"type": "str"},
            "store_logs": {"type": "bool", "default": False},
            "store_logs_region_id": {"type": "int"},
            "new_external_ips_count": {"type": "int"},
            "delete_external_ips": {"type": "list", "elements": "str"},
            "shared_cluster": {"type": "bool", "default": True},
            "vhost_zones": {"type": "list", "elements": "dict"},
            "upstream_zones": {"type": "list", "elements": "dict"},
            "labels": {"type": "dict"},
            "wait": {"type": "int", "default": 600},
            "update_interval": {"type": "int", "default": 5},
        },
        required_one_of=[["id", "name"]],
        mutually_exclusive=[["id", "name"]],
        supports_check_mode=True,
    )

    if module.params["state"] == "absent":
        lb_instance = ScLbInstanceDelete(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            lb_type="l4",
            lb_id=module.params.get("id"),
            lb_name=module.params.get("name"),
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
    else:
        lb_instance = ScLbInstanceL4CreateUpdate(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            lb_id=module.params.get("id"),
            name=module.params.get("name"),
            location_id=module.params.get("location_id"),
            cluster_id=module.params.get("cluster_id"),
            store_logs=module.params.get("store_logs"),
            store_logs_region_id=module.params.get("store_logs_region_id"),
            new_external_ips_count=module.params.get("new_external_ips_count"),
            delete_external_ips=module.params.get("delete_external_ips"),
            shared_cluster=module.params.get("shared_cluster"),
            vhost_zones=module.params.get("vhost_zones"),
            upstream_zones=module.params.get("upstream_zones"),
            labels=module.params.get("labels"),
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )

    try:
        result = lb_instance.run()
        module.exit_json(**result)
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
