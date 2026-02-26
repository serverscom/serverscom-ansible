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
module: sc_cloud_computing_instance_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Information about cloud computing instance
description: Return detailed information about specific cloud computing instance.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
  instance_id:
    type: str
    description:
      - Id of the instance.
      - Mutually exclusive with I(name).
      - Either I(instance_id) or I(name) is required.

  name:
    type: str
    aliases: [instance_name]
    description:
      - Id of the instance.
      - Mutually exclusive with I(instance_id).
      - Either I(instance_id) or I(name) is required.
      - Module will fail if more than one instance found.

  region_id:
    type: int
    description:
      - Region ID to search instance by name.
      - Used only for I(name).
"""

RETURN = """
id:
  type: str
  description:
    - A unique identifier of a cloud instance.
  returned: on success
region_id:
  type: int
  description:
    - A unique identifier of the cloud region where an instance is deployed.
  returned: on success
region_code:
  type: str
  description:
    - A technical identifier of a cloud region.
  returned: on success
flavor_id:
  type: str
  description:
    - A unique identifier of a cloud flavor this instance belongs to.
  returned: on success
flavor_name:
  type: str
  description:
    - A name of a cloud flavor.
  returned: on success
image_id:
  type: str
  description:
    - A unique identifier of a cloud image.
  returned: on success
image_name:
  type: str
  description:
    - A name of a cloud image.
    - May be absent if the image was removed.
  returned: on success
name:
  type: str
  description:
    - A name given to the cloud instance.
  returned: on success
openstack_uuid:
  type: str
  description:
    - A unique identifier of the instance in the OpenStack API.
    - May be null if the instance is not yet created.
  returned: on success
status:
  type: str
  description:
    - Current status for the instance.
    - ACTIVE - a normal, operational status of a cloud instance.
    - SWITCHED_OFF, SWITCHING_OFF, SWITCHING_ON, REBOOTING - power states
      for ACTIVE instance.
    - PENDING - order for new instance is been processed.
    - CREATING, BUILDING, REBUILDING, PROVISIONING, DELETING and DELETED
      stages of lifecycle.
    - AWAITING_UPGRADE_CONFIRM - instance is waiting for confirm
      (instances are autoconfirm in 72hr.)
    - UPGRADING, REVERTING_UPGRADE - stages of upgrade lifecycle.
    - CREATING_SNAPSHOT - Instance snapshot is creating.
    - BUSY - Instance is not available for API operations.
    - ERROR - Instance was failed or wasn't created.
    - KEYPAIR_NOT_FOUND - SSH key wasn't found, please check if you are
      using a correct key.
    - QUOTA_EXCEEDED - at creation time, chosen flavor exceeded quota.
      Please contact support for raising quota.
    - RESCUING, RESCUE - states for rescue operation for instance.
  returned: on success
public_ipv4_address:
  type: str
  description:
    - An external IPv4 address assigned for a public network.
    - May be null if the public interface was detached.
  returned: on success
public_ipv6_address:
  type: str
  description:
    - An IPv6 address assigned for a public network.
    - May be null if no IPv6 was ordered or interface was detached.
  returned: on success
private_ipv4_address:
  type: str
  description:
    - An internal IPv4 address for a private network.
    - May be null if no private network is connected.
  returned: on success
local_ipv4_address:
  type: str
  description:
    - A local IPv4 used for private-server connection within a region.
    - May be null if no private network is connected.
  returned: on success
ipv6_enabled:
  type: bool
  description:
    - Whether the IPv6 option is enabled.
  returned: on success
gpn_enabled:
  type: bool
  description:
    - Whether Global Private Network is enabled.
  returned: on success
vpn2gpn_instance:
  type: dict
  description:
    - Details of the VPN-to-GPN instance, or null if none.
  contains:
    id:
      type: int
      description:
        - VPN2GPN instance ID.
      returned: on success
    name:
      type: str
      description:
        - VPN2GPN instance name.
      returned: on success
  returned: on success
backup_copies:
  type: int
  description:
    - Number of backup copies for the instance.
  returned: on success
public_port_blocked:
  type: bool
  description:
    - Whether the public port of the instance is blocked.
  returned: on success
labels:
  type: dict
  description:
    - Labels associated with the resource.
  returned: on success
created_at:
  type: str
  description:
    - A date and time when the instance was created.
  returned: on success
updated_at:
  type: str
  description:
    - A date and time of the instance's last update.
  returned: on success
api_url:
  type: str
  description:
    - URL for the failed request.
  returned: on failure
status_code:
  type: int
  description:
    - HTTP status code of the failed request.
  returned: on failure
"""

EXAMPLES = """
- name: List all flavors
  sc_cloud_computing_instance_info:
    token: '{{ sc_token }}'
    instance_id: M7e5Ba2v
  register: instance

- name: Print information about instance
  debug:
    msg: |
      Instance {{ instance.name }} has IP {{ instance.public_ipv4_address }}

- name: Waiting for instance to become ACTIVE
  sc_cloud_computing_instance_info:
    token: '{{ sc_token }}'
    instance_id: M7e5Ba2v
  register: instance
  until: instance.status == 'ACTIVE'
  delay: 10
  retries: 30
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_cloud_computing import (
    ScCloudComputingInstanceInfo,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "instance_id": {},
            "name": {"aliases": ["instance_name"]},
            "region_id": {"type": "int"},
        },
        required_one_of=[["name", "instance_id"]],
        supports_check_mode=True,
    )
    try:
        instance = ScCloudComputingInstanceInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            instance_id=module.params["instance_id"],
            name=module.params["name"],
            region_id=module.params["region_id"],
        )
        module.exit_json(**instance.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
