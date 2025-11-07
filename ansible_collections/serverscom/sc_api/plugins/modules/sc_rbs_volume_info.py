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
module: sc_rbs_volume_info
version_added: "1.0.0"
author: "Aleksandr Chudinov (@chal)"
short_description: Returns list of Remote Block Storage volumes.
description: >
    Returns list of Remote Block Storage volumes for specified search criteria.

options:
    endpoint:
      type: str
      required: false
      default: https://api.servers.com/v1
      description:
        - API endpoint.
    token:
      type: str
      required: true
      description:
        - API token.
    label_selector:
      type: str
      required: false
      description:
        - A selector to filter volumes by labels.
        - More info at https://developers.servers.com/api-documentation/v1/#section/Labels/Labels-selector
    search_pattern:
      type: str
      required: false
      description:
        - A string to filter volumes by name or ID.
        - If specified, the module will return only volumes names of which match the provided string.
    location_id:
      type: str
      required: false
      description:
        - Location identifier.
    location_code:
      type: str
      required: false
      description:
        - Human-readable location slug (mutually exclusive with I(location_id)).
"""

RETURN = """
rbs_volumes:
  type: list
  elements: dict
  returned: on success
  description:
    - List of Remote Block Storage volumes.
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
    username:
      type: str
      description: Username to access the volume.
    password:
      type: str
      description: Password to access the volume.
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
    - name: List all available volumes in specific location specified by id
      serverscom.sc_api.sc_rbs_volume_info:
        token: "{{ api_token }}"
        location_id: 34
      register: result

    - name: List volume with "myvolume" in name in ams1 location
      serverscom.sc_api.sc_rbs_volume_info:
        token: "{{ api_token }}"
        location_code: ams1
        search_pattern: myvolume
      register: result

    - name: List volume with specific labels in all locations
      serverscom.sc_api.sc_rbs_volume_info:
        token: "{{ api_token }}"
        label_selector: "environment==staging"
      register: result
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScRBSVolumeList
)


def main():
    module = AnsibleModule(
        argument_spec={
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT, "required": False},
            "token": {"type": "str", "no_log": True, "required": True},
            "label_selector": {"type": "str", "required": False},
            "search_pattern": {"type": "str", "required": False},
            "location_id": {"type": "str", "required": False},
            "location_code": {"type": "str", "required": False}
        },
        supports_check_mode=True,
        required_one_of=[
            ['label_selector', 'search_pattern', 'location_id', 'location_code']
        ],

        mutually_exclusive=[
            ['location_id', 'location_code'],
        ],
    )
    try:
        sc_os = ScRBSVolumeList(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            label_selector=module.params.get("label_selector"),
            search_pattern=module.params.get("search_pattern"),
            location_id=module.params.get("location_id"),
            location_code=module.params.get("location_code"),
        )
        module.exit_json(**sc_os.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
