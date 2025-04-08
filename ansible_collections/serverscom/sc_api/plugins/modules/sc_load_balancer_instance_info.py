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
  - For creation, "name", "location_id", "vhost_zones", and "upstream_zones" are required.
  - For update, "id" is required along with any parameters to modify.
  - For deletion, either "id" or "name" must be provided, but not both.
options:
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
      - Unique identifier of the load balancer.
      - Required for update operations; for deletion, either this or "name" must be provided.
    required: false
    type: str
  name:
    description:
      - Name for the load balancer.
      - Required for creation; for deletion, either this or "id" must be provided.
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
type:
  type: str
  description: Load Balancer instance type.
  returned: on success
  sample: "l4"

id:
  type: str
  description: A unique identifier of a balancer.
  returned: on success
  sample: "d1FVescv"

name:
  type: str
  description: A human-readable name of a balancer.
  returned: on success
  sample: "my-load-balancer"

location_id:
  type: int
  description: A unique identifier of the balancer's location.
  returned: on success
  sample: 101

cluster_id:
  type: str
  description: A unique identifier of a dedicated cluster where the balancer is deployed. Null if on a shared cluster.
  returned: when shared_cluster is false
  sample: "iLuK3Pa2"

shared_cluster:
  type: bool
  description: Indicates whether the balancer is hosted on a shared cluster.
  returned: on success
  sample: false

store_logs:
  type: bool
  description: Indicates if logs storage is enabled.
  returned: on success
  sample: true

store_logs_region_id:
  type: int
  description: Cloud region ID where logs are stored.
  returned: when store_logs is true
  sample: 5

external_addresses:
  type: list
  elements: str
  description: List of public IP addresses assigned to the balancer.
  returned: on success

labels:
  type: dict
  description: Labels associated with the balancer resource.
  returned: on success
  sample: {"env": "prod", "app": "web"}

created_at:
  type: str
  description: The date and time when the balancer was created.
  returned: on success
  sample: "2023-01-01T12:00:00Z"

updated_at:
  type: str
  description: The date and time of the balancer's last update.
  returned: on success
  sample: "2023-01-02T15:30:00Z"

status:
  type: str
  description: The current state of the balancer.
  returned: on success, or when fail_on_absent is false
  choices: ["pending", "in_process", "active", "absent"]
  sample: "active"

vhost_zones:
  description: List of vhost zones associated with the Load Balancer instance.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: A unique identifier of a vhost zone.
      type: str
      sample: "vhost-zone-123"
    ports:
      description: An array of port numbers.
      type: list
      elements: int
      sample: [80, 443]

    # L4-specific fields
    upstream_id:
      description: A unique identifier of an associated upstream group. (L4 only)
      type: str
      sample: "upstream-456"
    udp:
      description: Indicates whether UDP traffic balancing is enabled. (L4 only)
      type: bool
      default: false
    proxy_protocol:
      description: Indicates if the proxy protocol is enabled. (L4 only)
      type: bool
      default: false
    acl_allow:
      description: Indicates if ACL rules are applied for balancing. (L4 only)
      type: bool
      default: false
    acl_list:
      description: An array of ACL rules. (L4 only)
      type: list
      elements: str
      sample: ["192.168.1.1", "10.0.0.0/8"]

    # L7-specific fields
    ssl:
      description: Indicates if SSL termination is enabled. (L7 only)
      type: bool
      default: false
    http2:
      description: Indicates if HTTP/2 protocol is enabled. (L7 only)
      type: bool
      default: false
    http_to_https_redirect:
      description: Indicates if HTTP is redirected to HTTPS. (L7 only)
      type: bool
      default: false
    http2_push_preload:
      description: Indicates HTTP/2 push preload status. (L7 only)
      type: bool
      default: false
    domains:
      description: List of target domains for the vhost zone. (L7 only)
      type: list
      elements: str
      sample: ["example.com", "api.example.com"]
    ssl_certificate_id:
      description: A unique identifier of an SSL certificate. (L7 only)
      type: str
      sample: "cert-789"
    tls_preset:
      description: Transport Layer Security (TLS) preset. (L7 only)
      type: str
      choices: ["TLSv1.2", "TLSv1.3"]
      default: "TLSv1.3"
    proxy_request_headers:
      description: Custom HTTP headers passing via the Load Balancer. (L7 only)
      type: list
      elements: dict
      contains:
        name:
          description: HTTP header name.
          type: str
          sample: "X-Forwarded-For"
        value:
          description: Header value.
          type: str
          sample: "client-ip"

upstream_zones:
  description: List of upstream zones associated with the Load Balancer instance.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: A unique identifier of the upstream zone.
      type: str
      sample: "upstream-zone-456"
    hc_interval:
      description: Interval for health checks in seconds.
      type: int
      default: 5
    hc_jitter:
      description: Jitter value in seconds for health checks.
      type: int
      default: 5

    # L4-specific fields
    hc_fails:
      description: Number of failed checks to remove an upstream server. (L4 only)
      type: int
      default: 1
    hc_passes:
      description: Number of successful checks to reintegrate an upstream server. (L4 only)
      type: int
      default: 3
    udp:
      description: Indicates whether UDP traffic balancing is enabled. (L4 only)
      type: bool
      default: false

    # L7-specific fields
    ssl:
      description: Indicates if SSL termination is enabled. (L7 only)
      type: bool
      default: false
    hc_domain:
      description: Health check domain. (L7 only)
      type: str
      sample: "health.example.com"
    hc_path:
      description: Health check URL path. (L7 only)
      type: str
      sample: "/status"
    hc_method:
      description: HTTP method for health checks. (L7 only)
      type: str
      choices: ["GET", "HEAD"]
      default: "GET"
    hc_mandatory:
      description: If enabled, new upstreams must pass health checks before being used. (L7 only)
      type: bool
      default: false
    sticky:
      description: Indicates whether a sticky cookie is enabled. (L7 only)
      type: bool
      default: true
    grpc:
      description: Indicates if gRPC is enabled. (L7 only)
      type: bool
      default: false
    hc_grpc_service:
      description: gRPC service name for health checks. (L7 only)
      type: str
      sample: "grpc-health-service"
    hc_grpc_status:
      description: Expected gRPC status code for a healthy upstream. (L7 only)
      type: int
      default: 0

    upstreams:
      description: List of upstream servers participating in load balancing.
      type: list
      elements: dict
      contains:
        ip:
          description: Upstream server IP address.
          type: str
          sample: "192.168.1.10"
        port:
          description: Upstream server port.
          type: int
          sample: 8080
        weight:
          description: Traffic weight assigned to the upstream.
          type: int
          default: 1
        max_fails:
          description: Maximum number of failures before marking upstream as unhealthy.
          type: int
          default: 0
        fail_timeout:
          description: Timeout period before marking an upstream as failed.
          type: int
          default: 30
        max_conns:
          description: Maximum number of connections allowed per upstream.
          type: int
          default: 63000
        status:
          description: Current health status of the upstream.
          type: str
          choices: ["online", "offline", "unknown"]
          sample: "online"

# L7 specific fields
domains:
  type: list
  elements: str
  description: The balancer distributes traffic for these domains.
  returned: when type is "l7"
  sample: ["example.com", "api.example.com"]

geoip:
  type: bool
  description: Indicates if GeoIP-based filtering is enabled.
  returned: when type is "l7"
  sample: false

redirect_http:
  type: bool
  description: Indicates if HTTP is redirected to HTTPS (deprecated).
  returned: when type is "l7"
  sample: false

proxy_protocol_enabled:
  type: bool
  description: Indicates if Proxy Protocol is enabled (deprecated).
  returned: when type is "l7"
  sample: false
"""

EXAMPLES = """
- name: Get LB instance info
  serverscom.sc_api.sc_load_balancer_instance_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    id: '0EUFRAox'
  register: lb_instance

- name: Report LB instance information
  ansible.builtin.debug:
    msg: "Server {{ lb_instance.name }} has the following IPs {{ lb_instance.external_addresses | join(', ') }}"

- name: Wait until instance is ready
  serverscom.sc_api.sc_load_balancer_instance_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    id: "0EUFRAox"
    fail_on_absent: False
  register: lb_instance
  until: lb_instance.status == "active"
  delay: 30
  retries: 300
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScLoadBalancerInstanceInfo,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "fail_on_absent": {"type": "bool", "default": True},
            "id": {"type": "str"},
            "name": {"type": "str"},
        },
        required_one_of=[["id", "name"]],
        mutually_exclusive=[["id", "name"]],
        supports_check_mode=True,
    )

    try:
        sc_load_balancer_instance_info = ScLoadBalancerInstanceInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            lb_instance_id=module.params.get("id"),
            lb_instance_name=module.params.get("name"),
            fail_on_absent=module.params["fail_on_absent"],
        )
        module.exit_json(**sc_load_balancer_instance_info.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
