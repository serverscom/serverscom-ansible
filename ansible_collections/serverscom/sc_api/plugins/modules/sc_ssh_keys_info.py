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
module: sc_ssh_keys_info
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Return all registered ssh public keys.
description: >
    Return list of all registered ssh keys.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    label_selector:
        type: str
        description:
            - Search for bare metal servers with specific labels.
            - More info at https://developers.servers.com/api-documentation/v1/#section/Labels/Labels-selector
"""

RETURN = """
ssh_keys:
  type: list
  elements: dict
  returned: on success
  description:
    - List of registered SSH public keys.
    - Empty list if none registered.
  contains:
    name:
      type: str
      description:
        - Name of the key.
    fingerprint:
      type: str
      description:
        - Fingerprint of the public key.
    labels:
      type: dict
      description:
        - Labels attached to the key.
    created_at:
      type: str
      description:
        - Timestamp when the key was added.
    updated_at:
      type: str
      description:
        - Timestamp of the key last update.

api_url:
  type: str
  returned: on failure
  description:
    - URL of the failed request.

status_code:
  type: int
  returned: always
  description:
    - HTTP status code of the response.
"""

EXAMPLES = """
    - name: Add ssh key
      sc_ssh_keys_info:
      register: keys_list

    - debug: var=keys_list.ssh_keys
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_ssh_key import (
    ScSshKeysInfo,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "label_selector": {"type": "str"},
        },
        supports_check_mode=True,
    )
    try:
        sc_ssh_key = ScSshKeysInfo(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            label_selector=module.params.get("label_selector"),
        )
        module.exit_json(**sc_ssh_key.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
