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
module: sc_cloud_computing_instance
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Create or delete a cloud computing instance
description: >
    Allow to create/delete/reinstall/upgrade cloud instance.

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
      choices: [absent, present, reinstalled, upgraded]
      required: true
      description:
        - State of instance.
        - C(present) creates instance if it not present, but does not
          change parameters for existing instances.
        - C(absent) delete instance if it present.
        - C(reinstalled) performs reinstallation. I(image_id) or
          I(Image_regexp) are used, if not specified, old image
          is used.
        - C(reinstalled) is not idempotent, use 'when' for idempotency.
        - C(upgraded) performs upgrade (change of the flavor),
          if flavor of the current instance
          is different from existing flavor. It does not create a new instance.
        - C(present) requires additional information for creation.
        - C(absent) requires either C(id) or C(name).
        - If I(state)=C(absent), C(reinstalled) or C(upgraded)
          with C(name) and there are multiple instances with the same name,
          module fails.

    instance_id:
      type: str
      description:
        - ID of the instance for I(state)=C(absent).
        - Mutually exclusive with I(name)

    region_id:
      type: int
      description:
        - Id of the cloud region for the instance
        - Use M(sc_cloud_computing_regions_info) to get list of available
          regions.
        - Required for I(state)=C(present).
        - May be used for other I(state) to narrow search to one region with
          I(name).

    name:
      type: str
      description:
        - Name of the instance.
        - Will be used as hostname for the new instance.
        - Required for I(state)=C(present).
        - May be used for I(state)=C(absent) instead of I(instance_id).

    image_id:
      type: str
      description:
        - Id of the image or snapshot to build instance from.
        - Mutually exclusive with I(image_regexp).
        - Required for I(state)=C(present).
        - Used for I(state)=C(reinstalled) if present.
        - Ignored for I(state)=C(absent) and C(upgraded).

    image_regexp:
      type: str
      description:
        - Regular expression to use to find an image or a snapshot to
          build instance from.
        - Regular expressions are based on python 're' module.
        - First found image is used if few images matches.
        - Use I(image_id) for exact image selection.
        - Mutually exclusive with I(image_id).
        - Required for I(state)=C(present).
        - Used for I(state)=C(reinstalled) if present.
        - Ignored for I(state)=C(absent) and C(upgraded).

    flavor_id:
      type: str
      description:
        - Id of the flavor to use.
        - Some flavors may be needed for certain images.
        - Different flavors have different mothly price.
        - Mutually exclusive with I(flavor_name).
        - I(flavor_id) or I(flavor_name) is required for
          for I(state)=C(present) and C(upgraded).
        - Ignored for I(state)=C(absent) and C(reinstalled).

    flavor_name:
      type: str
      description:
        - Name of the flavor to use.
        - Flavor name is checked for exact match.
        - Some flavors may be needed for certain images.
        - Different flavors have different mothly price.
        - Mutually exclusive with I(flavor_id).
        - I(flavor_id) or I(flavor_name) is required for
          for I(state)=C(present) and C(upgraded).
        - Ignored for I(state)=C(absent) and C(reinstalled).

    gpn:
        type: bool
        default: false
        description:
          - Enable Global Private network for the instance.
          - Local Private network is always allocated for instances regardless
            of Global Private network status.
          - Is used only for for I(state)=C(present).

    ipv6:
        type: bool
        default: false
        description:
          - Enable IPv6.
          - Currently enable IPv6 only on public (internet) interface.
          - Is used only for for I(state)=C(present).

    ssh_key_fingerprint:
        type: str
        description:
          - Fingerprint of the public ssh key to use for user cloud-user.
          - Fingerprint must be registered. Use M(sc_ssh_key) to register
            public key.
          - Mutually exclusive with I(ssh_key_name)
          - Instance is created with password if no I(ssh_key_fingerprint)
            or I(ssh_key_name) is used.
          - Is used only for for I(state)=C(present).

    ssh_key_name:
        type: str
        description:
          - Name of the registered ssh public key to use for user cloud-user.
          - Key must be registered before use.
          - Mutually exclusive with I(ssh_key_fingerprint)
          - Instance is created with password if no I(ssh_key_fingerprint)
            or I(ssh_key_name) is used.
          - Is used only for for I(state)=C(present).

    backup_copies:
        type: int
        default: 5
        description:
          - Number of daily backups to keep.
          - Default value (if not specified) is 5.
          - Value C(0) disables daily backups.
          - Is used only for for I(state)=C(present).
          - Ignored for I(state)=C(absent).

    wait:
      type: int
      required: false
      default: 600
      description:
        - Time to wait until instance get to the desired state.
        - I(state)=C(present) waits for ACTIVE.
        - I(state)=C(absent) waits for instance to disappear.
        - Value C(0) is used to disable wait.
        - If C(0) is set, module works in 'fire-and-forget' mode.
        - ACTIVE state doesn't mean that instance is ready to accept ssh
          connections. Use M(wait_for_connection) module wait until instance
          finishes booting.
        - wait time is independent for I(retry_on_conflicts) and status wait.
        - If instance is in conflicting state, first module will retry up to
          I(wait) seconds to delete it, and then wait for I(wait) seconds for
          it do disappear.
        - I(state)=C(upgraded) may take a very long time, depending on the
          flavor, so large values (C(3600), C(14400)) are advised.

    update_interval:
      type: int
      required: false
      default: 5
      description:
        - Polling interval for waiting.
        - Every polling request is reducing API ratelimits.

    retry_on_conflicts:
      type: bool
      default: True
      description:
        - Retry delete requiest for I(state)=C(absent) if instance
          is in conflicting state (code 409).
        - Retries are controlled by wait/update_interval values.

    confirm_upgrade:
      type: bool
      default: true
      description:
       - Confirm upgrades.
       - Upgrades are autoconfirmed in 72 hours.
       - Used only for I(state)=C(upgraded), ignored of other I(state).
       - If instance is in the state AWAITING_UPGRADE_CONFIRM,
         calling M(cloud_computing_instance) with I(state)=C(upgraded)
"""

#  delete multiple?

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
- name: Delete instance by ID
  sc_cloud_computing_instance:
    token: '{{ sc_token }}'
    instance_id: M7e5Ba2v
    state: absent
    wait: 60
    update_interval: 5

- name: Delete instance by name in region 3
  sc_cloud_computing_instance:
    token: '{{ sc_token }}'
    name: test
    region_id: 3
    state: absent
    wait: 60
    update_interval: 5

"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScCloudComputingInstanceCreate,
    ScCloudComputingInstanceDelete
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'state': {
                'type': 'str',
                'choices': ['present', 'absent'],
                'required': True
            },
            'instance_id': {},
            'region_id': {'type': 'int'},
            'name': {},
            'image_id': {},
            'image_regexp': {},
            'flavor_id': {},
            'flavor_name': {},
            'gpn': {'type': 'bool', 'default': False},
            'ipv6': {'type': 'bool', 'default': False},
            'ssh_key_fingerprint': {},
            'ssh_key_name': {},
            'backup_copies': {'type': 'int', 'default': 5},
            'wait': {'type': 'int', 'default': 600},
            'update_interval': {'type': 'int', 'default': 5},
            'retry_on_conflicts': {'type': 'bool', 'default': True}
        },
        mutually_exclusive=[
            ['ssh_key_name', 'ssh_key_fingerprint'],
            ['name', 'instance_id'],
            ['flavor_name', 'flavor_id'],
            ['image_regexp', 'image_id']
        ],
        required_if=[
            [
                "state", "present",
                ["region_id"]
            ]
        ],
        supports_check_mode=True
    )
    try:
        if module.params['state'] == 'present':
            instance = ScCloudComputingInstanceCreate(
                endpoint=module.params['endpoint'],
                token=module.params['token'],
                region_id=module.params['region_id'],
                name=module.params['name'],
                image_id=module.params['image_id'],
                image_regexp=module.params['image_regexp'],
                flavor_id=module.params['flavor_id'],
                flavor_name=module.params['flavor_name'],
                gpn_enabled=module.params['gpn'],
                ipv6_enabled=module.params['ipv6'],
                ssh_key_fingerprint=module.params['ssh_key_fingerprint'],
                ssh_key_name=module.params['ssh_key_name'],
                backup_copies=module.params['backup_copies'],
                wait=module.params['wait'],
                update_interval=module.params['update_interval'],
                checkmode=module.check_mode
            )
        elif module.params['state'] == 'absent':
            instance = ScCloudComputingInstanceDelete(
                endpoint=module.params['endpoint'],
                token=module.params['token'],
                instance_id=module.params['instance_id'],
                region_id=module.params['region_id'],
                name=module.params['name'],
                wait=module.params['wait'],
                update_interval=module.params['update_interval'],
                retry_on_conflicts=module.params['retry_on_conflicts'],
                checkmode=module.check_mode
            )
        module.exit_json(**instance.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
