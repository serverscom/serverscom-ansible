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
module: sc_ssh_key
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Manage ssh key
description: >
    Add or remove ssh keys in the idempotent way.

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
      choices: ['present', 'absent']
      description:
        - State of the key.
        - If I(state)=C(present), module checks if there are other keys
          with the same name or fingerprint. If they are but are different
          (f.e. existing key with a given nave have different fingerprint)
          they are replaced with I(name) and I(public_key) values.
        - If I(state)=C(absent), module removes keys based both on name and
          fingerprint or fail if I(replace) is C(false).

    name:
      type: str
      required: false
      description:
        - Name of the key.
        - Required for I(state)=C(present).
        - Used for I(state)=C(absent) to remove keys by name.

    public_key:
      type: str
      required: false
      description:
        - public key in base64 (with type prefix, f.e. ssh-rss).
        - Used to calculate I(fingerprint).
        - Required for I(state)=C(present).

    fingerprint:
      type: str
      required: false
      description:
        - Fingerprint of the key.
        - Used for I(state)=C(absent).
        - If both I(fingerprint) and I(public_keys) are given,
          module returns error if they are from different keys.
        - Derived automatically from I(public_key) if needed.

    labels:
      type: dict
      required: false
      description:
        - Labels to attach to the key.
        - Used for I(state)=C(present).
        - If not specified, no labels will be attached.

    replace:
      type: bool
      default: false
      description:
        - Used for I(state)=C(present).
        - If set to C(false), module fails if other keys with the same name
          or fingerprint are present.
        - If set to C(true), remove conflicting keys.
"""

RETURN = """
name:
  type: str
  description:
    - Name of the SSH key.
  returned: on success
fingerprint:
  type: str
  description:
    - Fingerprint of the public key.
  returned: on success
labels:
  type: dict
  description:
    - Labels attached to the key.
  returned: on success
created_at:
  type: str
  description:
    - Timestamp when the key was added.
  returned: on success
updated_at:
  type: str
  description:
    - Timestamp of the key's last update.
  returned: on success
"""

EXAMPLES = """
    - name: Add ssh key
      sc_ssh_key:
        name: key42
        public_key: '{{ lookup("file", "~/.ssh/id_rsa.pub") }}'
        state: present

    - name: Remove ssh keys either matching name or fingerprint
      sc_ssh_key:
        name: redundant
        fingerprint: 58:e5:58:e9:38:10:82:57:d9:82:11:8c:f6:44:68:e8
        state: absent

    - name: Add key but fails if there is a different key with the same name
      sc_ssh_key:
        name: ci_key
        public_key: '{{ ci_public_key }}'
        state: present
        replace: false
"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScSshKey,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "required": True,
            },
            "name": {"type": "str"},
            "public_key": {"type": "str"},
            "fingerprint": {"type": "str"},
            "labels": {"type": "dict"},
            "replace": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )
    try:
        sc_ssh_key = ScSshKey(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            name=module.params["name"],
            state=module.params["state"],
            public_key=module.params["public_key"],
            fingerprint=module.params["fingerprint"],
            labels=module.params.get("labels"),
            replace=module.params["replace"],
            checkmode=module.check_mode,
        )
        module.exit_json(**sc_ssh_key.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
