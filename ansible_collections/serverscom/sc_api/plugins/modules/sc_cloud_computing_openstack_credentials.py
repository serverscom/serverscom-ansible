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
module: sc_cloud_computing_openstack_credentials
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Retrive credentials for Openstack API in this regions
description: >
    Return credentials for Openstack API this region.

notes:
  - Please be careful with retrived information, passwords may be disclosed
    in log files.
  - Some functions may fail if performed directly through openstack API.
  - Tenant-level networks are allocated by Servers.com Public API
    and can not be created through Openstack API.
  - Creation of new instances should always be done through Public API,
    direct calls to Openstack may fail.
  - Some low-level modifications of objects through Openstack API may
    be incompatible with Public API.
  - It's safe to rebuild and reboot instances through Openstack API.

extends_documentation_fragment: serverscom.sc_api.sc_api_auth

options:
    region_id:
      type: int
      required: true
      description:
        - Id of cloud computing region.
        - Use I(serverscom.sc_api.sc_cloud_computing_regions_info) module
          to retrive list of available regions.
"""

RETURN = """
cloud_flavors:
  type: complex
  description:
    - Credentials for the region.
    - Be careful with debug output for this module as it return passwords
      in plain text.
    - OS_PROJECT_DOMAIN_NAME and OS_USER_DOMAIN_NAME are always 'default'.

  contains:
    url:
      type: str
      description:
        - Authorization endpoint for Openstack API.
        - Corresponds to OS_AUTH_URL.

    tenant_name:
      type: str
      description:
        - Tenant name in Openstack API.
        - Corresponds to OS_TENANT_NAME or OS_PROJECT_NAME.

    username:
      type: str
      description:
        - Username in Openstack API.
        - Corresponds to OS_USERNAME.

    password:
      type: str
      description:
        - Password for Openstack API.
        - In plain text. Be careful.
        - Corresponds to OS_PASSWORD.
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
- name: Get openstack credentials for region
  sc_cloud_computing_openstack_credentials:
    token: '{{ sc_token }}'
    region_id: 0
  register: os

- name: Retrive service catalog from Openstack
  os_auth:
    auth:
      auth_url: '{{ creds.url }}'
      username: '{{ creds.username }}'
      password: '{{ creds.password }}'
      project_name: '{{ creds.tenant_name }}'
  register: os

- name: Print service catalog
  debug: var=os.ansible_facts.service_catalog
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_cloud_computing import (
    ScCloudComputingOpenstackCredentials,
)

__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "region_id": {"type": "int", "required": True},
        },
        supports_check_mode=True,
    )
    try:
        creds = ScCloudComputingOpenstackCredentials(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            region_id=module.params["region_id"],
        )
        module.exit_json(**creds.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
