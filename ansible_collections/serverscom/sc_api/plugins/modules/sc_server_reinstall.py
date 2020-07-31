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
module: sc_server_reinstall
version_added: "2.10"
author: "George Shuklin (@amarao)"
short_description: Reinstall baremetal server.
description: >
    Reinstall the existing baremetal server. Existing data may be lost in
    the process. No guranteed data removal (some data may be left).
    No secure erase or wipe is performed during installation.
    Reinstallation request may fail for servers with custom hardware
    configuration (external drive shelves).

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

    name:
      aliases: [id]
      type: str
      required: true
      description:
        - ID of the server to reinstall.
        - Translates to server_id in API.

    hostname:
      type: str
      description:
        - Hostname for the server.
        - Module will retrive old hostname if not specified.
        - Translates to hostname in API.

    drives_layout_template:
        type: str
        choices: [raid1-simple, raid0-simple]
        description:
            - Mutually exclusive with i(drives_layout).
            - Provides a template to use instead of drives_layout
            - C(raid1-simple) uses two first drives to create RAID1,
              partition /boot (500Mb), swap (2Gb) and / (all other space).
            - C(raid0-simple) uses first drive as raid0 (or no raid in case
              of servers without hardware raid), and places /boot, swap
              and / on this drive.
            - This option is implemented by the module (it generates layout
              for drives['layout'] request to API based on built-in template).

    drives_layout:
      required: true
      type: list
      elements: dict
      description:
        - Mutually exclusive with I(drives_layout_template).
        - Partitioning of the drives during installation.
        - Translates to drives["layout"] in API.
        - List of configuration for each raid or stand-alone drive.
        - At least one layout should be provided.
        - Slot 0 must be used.
        - Partitioning should provide at least '/' (root) and /boot (for Linux)
          or 'C:\' for Windows. Only paritioning for dirve 'C:\' is supported
          for Windows.
      suboptions:
        slot_positions:
          required: true
          type: list
          elements: int
          description:
           - List of drive slots to use.
           - Count starts from slot 0.
           - Every slot may be used only once in one configration element.
           - Slot count is limited by number of physiscally availble drives
             in server.
        raid:
          type: int
          choices: [0, 1, 5, 6, 10, 50, 60]
          default: 0
          description:
            - Type of raid.
            - Every raid type (except C(0)) have own requirement for
              number of used drives in I(slot_positions).
            - If raid is None (not specified), raid0 is built.
            - If I(slots_positions) has only one device, it will be used
              as a device or as a raid0 with a single drive depending on
              hadrware raid capabilities. Systems with software raid will
              use drive 'as is'.

        partitions:

          description:
              - Partition layout for raid or device.
              - Paritioning will be skipped if not specified ('ignore' in API).
              - Old data may be left if no partitioning was performed.
          suboptions:
              target:
                type: str
                required: true
                description:
                  - Mountpoint for a partition.
                  - C(swap) is used as mount point for swap.
                  - At least C(/boot) and C(/) should be created for Linux.
                  - C(C:\\) should be created for Windows.
              fs:
                type: str
                description:
                  - Filesystem to use
                  - C(swap) is used for swap.

              size:
                type: int
                description:
                  - Size of partition in Mb
                  - Value of 0 is used to indicate 'fill mode'
                    (use all available space except for other partitions).
                  - Only one 'fill mode' partiiton may be present
                    in the layout.



    operating_system_id:
      type: str
      description:
        - id of the operating system to install on the server.
        - Module will retrive and reuse old operating system if
          not specified.

    ssh_keys:
      type: list
      elements: str
      description:
        - Array of fingerprints of public ssh keys to add for root user.
        - Keys must be registered before use.
        - Mutually exclusive with I(ssh_key_name).
        - Server is reinstalled with root password only if no I(ssh_keys) or
          I(ssh_key_name) specified.

    ssh_key_name:
      type: str
      description:
        - Name of a single ssh key to add to root user.
        - Mutually exclusive with I(ssh_keys).
        - Server is reinstalled with root password only if no I(ssh_keys) or
          I(ssh_key_name) specified.
        - Name is used to search fingerprint through ssh keys API requests.
        - Key should be registered.
        - This option is implemented by the module.

    wait:
        type: int
        default: 86400
        description:
            - Time to wait for server to change status to 'ready'
            - If wait is 0 or absent, task is succeeded
              sending reuest to API without waiting.
            - When server become 'ready' after reinstallation,
              it can still be in booting state for some time
              and do not answer ssh/ping request.
              Use M(wait_for_connection) module to wait server
              become available though ssh.

    update_interval:
        type: int
        default: 60
        description:
            - Interval in seconds for requests for server status.
            - Each update request reduces number of available API
              requests in accordance with ratelimit.
            - Minimal value is 10.
            - Ignored if I(wait)=C(0).
"""

RETURN = """

"""

EXAMPLES = """

"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text
import json
import itertools

requests = None

__metaclass__ = type


DEFAULT_API_ENDPOINT = 'https://api.servers.com/v1'


class APIError(Exception):
    def __init__(self, api_url, status_code, msg):
        self.api_url = api_url
        self.status_code = status_code
        self.msg = msg

    def fail(self):
        return_value = {'failed': True, 'msg': self.msg}
        if self.api_url:
            return_value['api_url'] = self.api_url
        if self.status_code:
            return_value['status_code'] = self.status_code
        return return_value


class MultiPage(object):

    per_page = 100

    def __init__(self, request):
        self.request = request

    def __iter__(self):
        self.session = requests.Session()
        self.next = self.request
        self.next.params.update({'per_page': self.per_page})
        return self

    def __next__(self):
        if self.next.url:
            prep_req = self.next.prepare()
            resp = self.session.send(prep_req)
            if resp.status_code == 401:
                raise APIError(
                    msg='401 Unauthorized. Check if token is valid.',
                    status_code=resp.status_code,
                    api_url=self.next.url
                )
            if resp.status_code != 200:
                raise APIError(
                    msg=f'API Error: {resp.content }',
                    status_code=resp.status_code,
                    api_url=self.next_url
                )
            self.next.url = resp.links.get('next', {'url': None})['url']
            try:
                return resp.json()
            except ValueError as e:
                raise APIError(
                    msg=f'API decoding error: {str(e)}, data: {resp.content}',
                    status_code=resp.status_code,
                    api_url=self.next_url
                )
        else:
            raise StopIteration


class API(object):
    def __init__(self, endpoint, token):
        self.endpoint = endpoint
        self.token = token

    def start_request(self, path, query):
        req = requests.Request('GET', self.endpoint + path, params=query)
        req.headers['Authorization'] = f'Bearer {self.token}'
        return req


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'name': {'type': 'str', 'required': True, 'aliases': ['id']},
            'hostname': {'type': 'str'},
            'drives_layout_template': {
                'type': 'str',
                'choices': ['raid1-simple', 'raid0-simple']
            },
            'drives_layout': {'type': 'list'},
            'operating_system_id': {'type': 'str'},
            'ssh_keys': {'type': 'list'},
            'ssh_key_name': {'type': 'str'},
            'wait': {'type': 'int', 'default': 86400},
            'update_interval': {'type': 'int', 'default': 60},
        },
        supports_check_mode=True
    )
    try:
        global requests
        import requests
    except Exception:
        module.exit_fail(msg='This module needs requests library.')
    # module.exit_json(**sc_info.run())


if __name__ == '__main__':
    main()
