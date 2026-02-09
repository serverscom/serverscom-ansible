#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2026, Servers.com
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
module: sc_sbm_server_labels
version_added: "1.0.0"
author: "Servers.com Team (@serverscom)"
short_description: Update labels on an SBM (Scalable Baremetal) server
description: >
    Update the labels associated with a Scalable Baremetal server.
    Labels are key-value pairs that can be used for filtering and
    organizing servers.
extends_documentation_fragment: serverscom.sc_api.sc_sbm

options:
    server_id:
      type: str
      required: true
      description:
        - ID of the SBM server to update.

    labels:
      type: dict
      required: true
      description:
        - Labels to set on the server.
        - This replaces all existing labels.
        - Use an empty dict to remove all labels.
"""

RETURN = """
id:
  type: str
  description:
    - Unique identifier of the server.
  returned: on success

labels:
  type: dict
  description:
    - Labels associated with the server after update.
  returned: on success

api_url:
  description: URL for the failed request.
  returned: on failure
  type: str

status_code:
  description: Status code for the request.
  returned: on failure
  type: int
"""

EXAMPLES = """
- name: Set labels on an SBM server
  serverscom.sc_api.sc_sbm_server_labels:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
    labels:
      environment: production
      service: my-web-app
  register: result

- name: Remove all labels
  serverscom.sc_api.sc_sbm_server_labels:
    token: '{{ sc_token }}'
    server_id: 'abc123xyz'
    labels: {}
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_sbm import (
    ScSbmServerLabels,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"type": "str", "default": DEFAULT_API_ENDPOINT},
            "server_id": {"type": "str", "required": True},
            "labels": {"type": "dict", "required": True},
        },
        supports_check_mode=True,
    )
    try:
        labels = ScSbmServerLabels(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params["server_id"],
            labels=module.params["labels"],
            checkmode=module.check_mode,
        )
        module.exit_json(**labels.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
