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
module: sc_cloud_computing_instance_state
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Manage instance states
description: >
    Allow to control power state and rescue mode for instance.
    This module does not allow removal and creation of the instance,
    use M(sc_cloud_computing_instance) with state=present/absent.

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

    state:
      type: str
      required: true
      choices: ['shutdown', 'rescue', 'normal', 'rebooted']
      description:
        - Make sure instance in I(state) mode.
        - Module will fail if operation is impossible (f.e. migrating)
          or absent.
        - C(shutdown) shutdown instance.
        - C(rescue) reboot instance in rescue mode.
        - C(normal) turn instanse on or exit in rescue mode.
        - C(rebooted) reboot instance. This state cause non non-idempotent
          action.

    name:
      type: str
      aliases: [instance_name]
      description:
        - Name of the instance to set PTR records for.
        - If more than one server with a given name found, module will fail.
        - Use I(instance_id) for precise identification.
        - Mutually exclusive with I(instance_id).

    instance_id:
      type: str
      description:
        - Id of the instance to manage PTR records for.
        - Mutually exclusive with I(name).

    region_id:
      type: int
      description:
        - Region ID to search instance by name.
        - All regions are searched if not specified.
        - Used only if I(name) present.

    wait:
      type: int
      required: false
      default: 600
      description:
        - Time to wait until instance get to the desired state.
        - I(state)=C(shutdown) waits for SWITCHED_OFF.
        - I(state)=C(rescue) waits for RESCUE.
        - I(state)=C(normal) waits for ACTIVE.
        - I(state)=C(rebooted) waits for ACTIVE.
        - Value C(0) is used to disable wait.
        - If C(0) is set, module works in 'fire-and-forget' mode.
        - ACTIVE state doesn't mean that instance is ready to accept ssh
          connections. Use M(wait_for_connection) module wait until instance
          finishes booting. handlers or when statement may be used
          to preserve idempotency.

    update_interval:
      type: int
      required: false
      default: 5
      description:
        - Polling interval for waiting.
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
ipv6:
  type: bool
  description:
    - Flag if IPv6 was enabled for instance.
  returned: on success
gpn:
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
- name: Shutdown instance
  sc_cloud_computing_instance_state:
    token: '{{ sc_token }}'
    instance_id: M7e5Ba2v
    state: shutdown
    wait: 60

- name: Switch to rescue mode by name
  sc_cloud_computing_instance_state:
    token: '{{ sc_token }}'
    name: myinstance
    region_id: 3
    state: rescue
    wait: 600

- name: Switch instance to normal mode
  sc_cloud_computing_instance_state:
    token: '{{ sc_token }}'
    name: test4
    state: normal

- name: Reboot instance
  sc_cloud_computing_instance_state:
    token: '{{ sc_token }}'
    name: app
    state: rebooted
  when: reboot_condition
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
import json
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScCloudComputingInstanceState
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'state': {
                'type': 'str',
                'choices': ['shutdown', 'normal', 'rescue', 'rebooted'],
                'required': True
            },
            'instance_id': {},
            'name': {'aliases': ['instance_name']},
            'region_id': {'type': 'int'},
            'wait': {'type': 'int', 'default': 600},
            'update_interval': {'type': 'int', 'default': 5}
        },
        mutually_exclusive=[
            ['name', 'instance_id']
        ],
        required_one_of=[
            ["name", "instance_id"]
        ],
        supports_check_mode=True
    )
    try:
        instance_state = ScCloudComputingInstanceState(
            endpoint=module.params['endpoint'],
            token=module.params['token'],
            state=module.params['state'],
            instance_id=module.params['instance_id'],
            name=module.params['name'],
            region_id=module.params['region_id'],
            wait=module.params['wait'],
            update_interval=module.params['update_interval'],
            checkmode=module.check_mode
        )
        module.exit_json(**instance_state.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
