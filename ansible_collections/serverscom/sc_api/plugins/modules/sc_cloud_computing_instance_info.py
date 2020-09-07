#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2020, Servers.com
# GNU General Public License v3.0
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import (absolute_import, division, print_function)


__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = """
---
module: sc_cloud_computing_instance_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Information about cloud computing instance
description: >
    Return information about cloud computing instance.

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
        - You can create token for you account in https://portal.servers.com
          in Profile -> Public API section.

    instance_id:
      type: str
      description:
        - Id of the instance.
        - Mutually exclusive with I(name)
        - Either I(instance_id) or I(name) is required.

    name:
      type: str
      aliases: [instance_name]
      description:
        - Id of the instance.
        - Mutually exclusive with I(instance_id)
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
    - Id of the instance.
  returned: on success
region_id:
  type: int
  description:
    - Id of the region.
    - Same as in I(region_id).
  returned: on success
region_code:
  type: str
  description:
    - Human-readable code for region.
  returned: on success
flavor_id:
  type: str
  description:
    - Id of the instance's flavor.
  returned: on success
flavor_name:
  type: str
  description:
    - Human-readable name of the instance's flavor.
  returned: on success
image_id:
  type: str
  description:
    - Id of the image or snapshot used for instance build/rebuild.
  returned: on success
image_name:
  type: str
  description:
    - Name of the image.
    - May be absent if image was removed.
  returned: on success
name:
  type: str
  description:
    - Name of the instance.
  returned: on success
openstack_uuid:
  type: str
  description:
    - UUID of the instance in the Openstack API.
    - May be missing at some stages of lifecycle.
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
    - IPv4 address for instance.
    - May be missing if public inteface was detached via Openstack API.
  returned: on success
public_ipv6_address:
  type: str
  description:
    - IPv5 address for instance.
    - May be missing if no IPv6 address was ordered or public inteface
     was detached via Openstack API.
  returned: on success
private_ipv4_address:
  type: str
  description:
    - IPv4 address for instance.
    - May be missing if no private network is connected to the instance.
  returned: on success
ipv6_enabled:
  type: bool
  description:
    - Flag if IPv6 was enabled for instance.
  returned: on success
gpn_enabled:
  type: bool
  description:
    - Flag is Global Private Network was enabled for instance.
    - Flag may not prepresent private_ipv4_address if private interface
      was detached via Openstack API.
  returned: on success
created_at:
  type: str
  description:
    - Date of creation of the instance.
  returned: on success
updated_at:
  type: str
  description:
    - Date of last update for the instance.
  returned: on success

api_url:
    description: URL for the failed request
    type: str
    returned: on failure

status_code:
    description: Status code for the request
    type: int
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
import json
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScCloudComputingInstanceInfo
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'instance_id': {},
            'name': {'aliases': ['instance_name']},
            'region_id': {'type': 'int'}
        },
        required_one_of=[['name', 'instance_id']],
        supports_check_mode=True
    )
    try:
        instance = ScCloudComputingInstanceInfo(
            endpoint=module.params['endpoint'],
            token=module.params['token'],
            instance_id=module.params['instance_id'],
            name=module.params['name'],
            region_id=module.params['region_id']
        )
        module.exit_json(**instance.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
