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
module: sc_cloud_computing_instances_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: List of cloud computing instances
description: >
    Return list of all instances in a given region

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    region_id:
      type: int
      description:
        - Id of cloud computing region to filter.
        - Use I(serverscom.sc_api.sc_cloud_computing_regions_info) module
          to retrive list of available regions.
        - Module returns instances for all regions if I(region_id) is not
          specified.
    label_selector:
        type: str
        description:
            - Search for bare metal servers with specific labels.
            - More info at https://developers.servers.com/api-documentation/v1/#section/Labels/Labels-selector
"""

RETURN = """
cloud_instances:
  description: List of available flavors for region.
  type: list
  elements: dict
  contains:
    id:
      type: str
      description:
        - Id of the instance.
    region_id:
      type: int
      description:
        - Id of the region.
        - Same as in I(region_id).
    region_code:
      type: str
      description:
        - Human-readable code for region.
    flavor_id:
      type: str
      description:
        - Id of the instance's flavor.
    flavor_name:
      type: str
      description:
        - Human-readable name of the instance's flavor.
    image_id:
      type: str
      description:
        - Id of the image or snapshot used for instance build/rebuild.
    image_name:
      type: str
      description:
        - Name of the image.
        - May be absent if image was removed.
    name:
      type: str
      description:
        - Name of the instance.
    openstack_uuid:
      type: str
      description:
        - UUID of the instance in the Openstack API.
        - May be missing at some stages of lifecycle.

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
    public_ipv4_address:
      type: str
      description:
        - IPv4 address for instance.
        - May be missing if public inteface was detached via Openstack API.
    public_ipv6_address:
      type: str
      description:
        - IPv5 address for instance.
        - May be missing if no IPv6 address was ordered or public inteface
         was detached via Openstack API.
    private_ipv4_address:
      type: str
      description:
        - IPv4 address for instance.
        - May be missing if no private network is connected to the instance.
    local_ipv4_address:
      type: str
      description:
        - Local IP.
        - May be null if no local network is connected to the instance.
      returned: on success
    ipv6_enabled:
      type: bool
      description:
        - Flag if IPv6 was enabled for instance.
    gpn_enabled:
      type: bool
      description:
        - Flag is Global Private Network was enabled for instance.
        - Flag may not prepresent private_ipv4_address if private interface
          was detached via Openstack API.
    vpn2gpn_instance:
      type: dict
      description:
        - VPN-to-GPN instance details or null.
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
        - Number of backup copies.
      returned: on success
    public_port_blocked:
      type: bool
      description:
        - Whether the public port of the instance is blocked.
      returned: on success
    labels:
      type: dict
      description:
        - Labels associated with the instance.
      returned: on success
    created_at:
      type: str
      description:
        - Date of creation of the instance.
    updated_at:
      type: str
      description:
        - Date of last update for the instance.
  returned: on success

api_url:
    description: URL for the failed request
    returned: on failure
    type: str

status_code:
    description: Status code for the request
    returned: always
    type: int
"""

EXAMPLES = """
    - name: List all flavors
      sc_cloud_computing_instances_info:
        token: '{{ sc_token }}'
        region_id: 0
        label_selector: "environment==staging"
      register: flavors

    - name: List all instances in the region
      debug: var=sc_cloud_computing_instances_info.cloud_instances
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_cloud_computing import (
    ScCloudComputingInstancesInfo,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "region_id": {"type": "int"},
            "label_selector": {"type": "str"},
        },
        supports_check_mode=True,
    )
    try:
        instances = ScCloudComputingInstancesInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            region_id=module.params["region_id"],
            label_selector=module.params.get("label_selector"),
        )
        module.exit_json(**instances.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
