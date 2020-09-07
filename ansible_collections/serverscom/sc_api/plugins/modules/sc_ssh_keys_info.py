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
module: sc_ssh_keys_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Return all registered ssh public keys.
description: >
    Return list of all registered ssh keys.

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
"""

RETURN = """
ssh_keys:
  type: complex
  description:
    - List of registered ssh public keys
    - Can be empty if no keys were registered.
  contains:
    name:
      type: str
      description:
        - Name of the key
    fingerprint:
      type: str
      description:
        - Fingerprint of the public key.
    created_at:
      type: str
      description:
        - Date this key was registered.
    updated_at:
      type: str
      description:
        - Date this key was updated last time.
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
    - name: Add ssh key
      sc_ssh_keys_info:
      register: keys_list

    - debug: var=keys_list.ssh_keys
"""


from ansible.module_utils.basic import AnsibleModule
import json
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScSshKeysInfo
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
        },
        supports_check_mode=True
    )
    try:
        sc_ssh_key = ScSshKeysInfo(
            endpoint=module.params['endpoint'],
            token=module.params['token'],
        )
        module.exit_json(**sc_ssh_key.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
