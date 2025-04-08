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
module: sc_load_balancer_instances_list
version_added: "1.0.0"
author: "Volodymyr Rudniev (@koef)"
short_description: Retrieve information about Load Balancer instances.
description: >
  - This module fetches details about Load Balancer instances from the Public API.
  - Returns information such as ID, name, type, status, and associated metadata.

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

  name:
    type: str
    required: false
    description:
      - A human-readable name of a Load Balancer.

  type:
    type: str
    description: Load Balancer instance type.
    required: false
    choices: ["l4", "l7"]
"""

RETURN = """
load_balancer_instances:
  description: A list of balancer instances.
  type: list
  elements: dict
  contains:
    id:
      type: str
      description: A unique identifier of a balancer.
      sample: "G6MqJy1l"

    name:
      type: str
      description: A human-readable name of a balancer.
      sample: "some-balancer"

    type:
      type: str
      description: Load Balancer instance type.
      sample: "l4"

    status:
      type: str
      description: The current state of the balancer.
      sample: "active"

    external_addresses:
      type: list
      description: List of public IP addresses assigned to the balancer.
      elements: str

    location_id:
      type: int
      description: A unique identifier for the balancer's location.
      sample: 123

    cluster_id:
      type: str
      description: A unique identifier of a dedicated cluster where the balancer is deployed. Returned only if I(shared_cluster)=C(false).
      sample: "keeCh2Io"

    shared_cluster:
      type: bool
      description: Indicates whether the balancer is hosted on a shared cluster.
      sample: false

    labels:
      type: dict
      description: Labels associated with the load balancer resource.
      sample: {"env": "prod", "app": "web"}

    created_at:
      type: str
      description: The date and time when the balancer was created.
      sample: "2025-01-23T00:04:23Z"

    updated_at:
      type: str
      description: The date and time of the balancer's last update.
      sample: "2025-02-09T00:07:42Z"
  returned: on success
"""

EXAMPLES = """
- name: Get all LB instances
  serverscom.sc_api.sc_load_balancer_instances_list:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
  register: lb_instances_list

- name: Report LB instances information
  ansible.builtin.debug:
    msg: '{{ item }}'
  loop: '{{ lb_instances_list.load_balancer_instances }}'
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScLoadBalancerInstancesList,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "name": {"type": "str", "required": False},
            "type": {"type": "str", "required": False, "choices": ["l4", "l7"]},
        },
        supports_check_mode=True,
    )
    try:
        sc_load_balancer_instances_list = ScLoadBalancerInstancesList(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            name=module.params.get("name"),
            type=module.params.get("type"),
        )
        module.exit_json(**sc_load_balancer_instances_list.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
