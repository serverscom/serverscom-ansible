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
module: sc_rbs_volume
version_added: "1.0.0"
author: "Aleksandr Chudinov (@chal)"
short_description: Creates, updates or deletes Remote Block Storage volume.
description: >
    Creates, updates or deletes Remote Block Storage volume.
    Returns information about created or updated volume.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    name:
      type: str
      required: false
      description:
        - Volume name.
    volume_id:
      type: str
      required: false
      description:
        - Volume identifier.
        - If volume with specified volume_id does not exist, module will fail.
    state:
      type: str
      required: false
      choices: ["present", "absent"]
      default: present
      description:
        - State of the volume.
        - |
          Use C(present) to create or update a volume.
          Only name, size and labels can be updated.
        - Use C(absent) to delete a volume.
    size:
      type: int
      required: false
      description:
        - Size of the volume in GB.
        - Should be provided to create a new volume or increase size of existing one.
    location_id:
      type: int
      required: false
      description:
        - Location identifier. (mutually exclusive with I(location_name)).
        - This or location_code should be provided to create a new volume.
    location_code:
      type: str
      required: false
      description:
        - Human-readable location slug (mutually exclusive with I(location_id)).
        - This or location_id should be provided to create a new volume.
    flavor_id:
      type: int
      required: false
      description:
        - Identifier of the flavor (mutually exclusive with I(flavor_name)).
        - This or flavor_name should be provided to create a new volume.
    flavor_name:
      type: str
      required: false
      description:
        - Name of the flavor (mutually exclusive with I(flavor_id)).
        - This or flavor_id should be provided to create a new volume.
    labels:
      type: dict
      required: false
      description:
        - Labels to attach to the volume. If labels do not exist they will be created.
        - Replaces existing set of labels with provided one if labels exist.
        - Key-value pairs.
        - If omitted, existing labels will remain unchanged.
        - To remove all labels, set to an empty dict.
        - More info at https://developers.servers.com/api-documentation/v1/#section/Labels.
    wait:
      description:
        - |
          Maximum time in seconds to wait for the volume to reach
          the desired state after an action (e.g. deletion).
          Set to 0 to not wait.
      required: false
      type: int
      default: 600
    update_interval:
      description: Interval in seconds between status checks.
      type: int
      default: 5
"""

RETURN = """
rbs_volume:
  type: dict
  returned: on success
  description:
    - Info about Remote Block Storage volume.
    - Empty dict in case volume was deleted.
  contains:
    id:
      type: str
      description: A unique identifier of the volume.
    name:
      type: str
      description: Volume name.
    size:
      type: int
      description: Size of the volume in GB.
    status:
      type: str
      description: |
        Current status of the volume. Possible values: "creating", "pending", "active", "removing".
    labels:
      type: dict
      description: Volume labels.
    location_id:
      type: str
      description: Location identifier.
    location_code:
      type: str
      description: Location code (string representation of location).
    ip_address:
      type: str
      description: IP address of the volume.
    flavor_id:
      type: int
      description: Identifier of the flavor.
    flavor_name:
      type: str
      description: Name of the flavor.
    iops:
      type: float
      description: Input/Output Operations Per Second quota of the volume.
    bandwidth:
      type: float
      description: Bandwidth quota of the volume in MB/s.
    target_iqn:
      type: str
      description: iSCSI target Qualified Name.
    created_at:
      type: str
      description: Volume creation time.
    updated_at:
      type: str
      description: Last volume update time.
api_url:
    description: URL for the failed request
    returned: on failure
    type: str
status_code:
    description: Status code for the request
    returned: on failure
    type: int
"""

EXAMPLES = """
    - name: Create volume
      serverscom.sc_api.sc_rbs_volume:
        token: "{{ api_token }}"
        name: test_volume
        size: 100
        location_id: 34
        flavor_name: basic
        state: present

    - name: Increase volume size by id
      serverscom.sc_api.sc_rbs_volume:
        token: "{{ api_token }}"
        volume_id: y1aKReQG
        size: 200
        state: present

    - name: Increase volume size by name and update labels
      serverscom.sc_api.sc_rbs_volume:
        token: "{{ api_token }}"
        name: test_volume
        size: 250
        labels:
          environment: production
          project: website
        state: present

    - name: Delete volume
      serverscom.sc_api.sc_rbs_volume:
        token: "{{ api_token }}"
        volume_id: YRdG7dDz
        state: absent
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    scRBSVolumeCreateUpdateDelete
)


def main():
    module = AnsibleModule(
        argument_spec={
            "endpoint": {"type": "str", "required": False, "default": DEFAULT_API_ENDPOINT},
            "token": {"type": "str", "no_log": True, "required": True},
            "name": {"type": "str", "required": False},
            "volume_id": {"type": "str", "required": False},
            "state": {
                "type": "str",
                "required": False,
                "default": "present",
                "choices": ["present", "absent"]
            },
            "size": {"type": "int", "required": False},
            "location_id": {"type": "int", "required": False},
            "location_code": {"type": "str", "required": False},
            "flavor_id": {"type": "int", "required": False},
            "flavor_name": {"type": "str", "required": False},
            "labels": {"type": "dict", "required": False},
            "wait": {"type": "int", "required": False, "default": 600},
            "update_interval": {"type": "int", "required": False, "default": 5},
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ['location_id', 'volume_id'],
            ['flavor_id', 'volume_id'],
            ['location_code', 'volume_id'],
            ['flavor_name', 'volume_id'],
            ['location_id', 'location_code'],
            ['flavor_id', 'flavor_name'],
        ],
        required_one_of=[
            ['volume_id', 'name']
        ],
    )

    state = module.params["state"]

    if (
        state == "present"
        and module.params.get("volume_id")
        and any(
            [
                module.params.get("location_id"),
                module.params.get("flavor_id"),
                module.params.get("flavor_name"),
                module.params.get("location_code"),
            ]
        )
    ):
        module.fail_json(msg="Updating existing volume is not supported, except for size, name and labels.")

    rbs_volume = scRBSVolumeCreateUpdateDelete(endpoint=module.params["endpoint"],
                                               token=module.params["token"],
                                               name=module.params["name"],
                                               volume_id=module.params["volume_id"],
                                               size=module.params["size"],
                                               location_id=module.params["location_id"],
                                               location_code=module.params["location_code"],
                                               flavor_id=module.params["flavor_id"],
                                               flavor_name=module.params["flavor_name"],
                                               labels=module.params["labels"],
                                               wait=module.params["wait"],
                                               update_interval=module.params["update_interval"],
                                               checkmode=module.check_mode)
    try:
        if state == "present" and not module.params.get("volume_id"):
            result = rbs_volume.create_or_update_volume()
        elif state == "present" and module.params.get("volume_id"):
            result = rbs_volume.update_volume()
        elif state == "absent":
            result = rbs_volume.delete_volume()
        module.exit_json(**result)
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
