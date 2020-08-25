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
module: sc_cloud_computing_instance_reinstall
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Reinstall cloud computing instance
description: >
    Perform rebuild of the instance.

notes:
  - This module can wait for instance to become ACTIVE, but it does not
    wait for instance to start to reply on SSH/RDP. Use M(wait_for_connection)
    module to get completely operational instance.
  - This module fails if image/snapshot was removed and module is called
    without I(image_id) paramter.
  - Old data are irreversibly lost during instance rebuild.
  - Instance keeps the same authorization method (the same ssh key or the
    same password).
  - Instance keeps old userdata, old uuid and old hostname after rebuild.

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
      required: true
      description:
        - Id of the instance.

    image_id:
      type: str
      required: false
      description:
        - Id of the image.
        - Module will use current image for instance if not specified.

    wait_for_active:
      type: int
      required: false
      default: 300
      description:
        - Time to wait until instance become ACTIVE again.
        - Value C(0) is used to disable wait for ACTIVE status.
        - Does not affect rebuild wait time.
        - If instance is not become active in I(wait) seconds, module fails.

    wait_for_rebuilding:
      type: int
      required: false
      default: 60
      description:
        - Time to wait for instance switch to REBUILDING status.
        - Value C(0) is used to disable wait for REBUILDING state.
        - I(wait_for_rebuilding)=C(0) and non-zero I(wait_for_active)
          is not supported.
        - If both I(wait_for_rebuilding) and I(wait_for_active) set to C(0)
          module works in 'fire-and-forget' mode.

    update_interval:
      type: int
      required: false
      default: 5
      description:
        - Polling interval for waiting (both ACTIVE and REBUILDING).
        - Every polling request is reducing API ratelimits.
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
      (instances are autoconfirm in 24hr.)
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
from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    DEFAULT_API_ENDPOINT,
    ModuleError,
    ScCloudComputingInstanceReinstall
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'instance_id': {'type': 'str', 'required': True},
            'image_id': {},
            'wait_for_active': {'type': 'int', 'default': 300},
            'wait_for_rebuilding': {'type': 'int', 'default': 60},
            'update_interval': {'type': 'int', 'default': 5},
        },
        supports_check_mode=True
    )

    reinstall = ScCloudComputingInstanceReinstall(
        endpoint=module.params['endpoint'],
        token=module.params['token'],
        instance_id=module.params['instance_id'],
        image_id=module.params['image_id'],
        wait_for_active=module.params['wait_for_active'],
        wait_for_rebuilding=module.params['wait_for_rebuilding'],
        update_interval=module.params['update_interval'],
        checkmode=module.check_mode
    )
    try:
        module.exit_json(**reinstall.run())
    except ModuleError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
