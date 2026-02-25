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
module: sc_rbs_volume_credentials_reset
version_added: "1.0.0"
author: "Aleksandr Chudinov (@chal)"
short_description: Resets RBS volume credentials.
description: >
    Resets credentials for Remote Block Storage volume.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    volume_id:
      type: str
      required: false
      description:
        - Remote Block Storage volume identifier.
    name:
      type: str
      required: false
      description:
        - Volume name.
    wait:
      description:
        - |
          Maximum time in seconds to wait for the volume to reach
          the active state after credentials reset is performed.
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
rbs_volume_credentials:
  type: dict
  returned: on success
  description:
    - Remote Block Storage volume credentials.
    - Empty dict in case wait is set to 0 (module does not wait until credentials are successfully reset).
  contains:
    volume_id:
      type: str
      description: A unique identifier of the volume.
    username:
      type: str
      description: Username to access the volume.
    password:
      type: str
      description: Password to access the volume.
    target_iqn:
      type: str
      description: iSCSI Qualified Name of the volume.
    ip_address:
      type: str
      description: IP address of the volume.
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
    - name: Reset RBS volume credentials by volume ID
      serverscom.sc_api.sc_rbs_volume_credentials_reset:
        token: "{{ api_token }}"
        volume_id: YRdG7dDz
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScRBSVolumeCredentialsReset
)


def main():
    module = AnsibleModule(
        argument_spec={
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT, "required": False},
            "token": {"type": "str", "no_log": True, "required": True},
            "volume_id": {"type": "str", "required": False},
            "name": {"type": "str", "required": False},
            "wait": {"type": "int", "default": 600, "required": False},
            "update_interval": {"type": "int", "default": 5, "required": False}
        },
        supports_check_mode=True,
        required_one_of=[
            ['volume_id', 'name']
        ],
        mutually_exclusive=[
            ['volume_id', 'name']
        ],
    )
    try:
        sc_volume = ScRBSVolumeCredentialsReset(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            volume_id=module.params["volume_id"],
            name=module.params["name"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
        module.exit_json(**sc_volume.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
