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
module: sc_dedicated_server_info
version_added: "2.10"
author: "George Shuklin (@amarao)"
short_description: Information about existing dedicated server
description: >
    Retrive information about existing dedicated baremetal server.

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
        - ID of the server.
        - Translates to server_id in API.
        - If ID is malformed, error 400 is returned.

    fail_on_absent:
      type: bool
      default: true
      description:
        - Raise error if server is not found.
        - If set to false, absent (not found) server will have
          found=false in server info.
"""

RETURN = """
id:
  type: str
  description:
    - ID of the server
  returned: on success

title:
  type: str
  description:
    - title of server (used as hostname).
  returned: on success

type:
  type: str
  description:
    - always 'dedicated_server'
  returned: on success

rack_id:
  type: str
  description:
    - ID of rack where server is installed.
    - May be null if not supported.
  returned: on success

status:
  type: str
  description:
    - Status of server.
    - Values "init" and "pending" are transient.
    - Value "active" is a normal status for a server.
  returned: on success

operational_status:
  type: str
  description:
    - Maintanance operations for the server.
    - Value 'normal' is used for the server without any operations.
    - Value 'provisioning' is used for the server under provisioning.
    - Value 'installation' is used for reinstalled/installed server
      during OS installation process.
    - Value 'entering_rescue_mode' is used during reconfiguration of the server
      for the rescue mode.
    - Value 'exiting_rescue_mode' is used during reconfiguration of the server
      from rescue mode to normal.
    - Value 'rescue_mode' is used for server in rescue mode.
  returned: on success

power_status:
    type: str
    description:
      - Power state of the server.
      - Possible values are unknown, powering_on, powering_off, powered_off,
        powered_on (normal mode for working server), power_cycling (sequence of
        off on operations).
    returned: on success

configuration:
  type: str
  description:
      - Server configuration
  returned: on success

location_id:
  type: str
  description:
    - ID of the location of the server.
  returned: on success

location_code:
  type: str
  description:
    - Code for location of the server.
  returned: on success

private_ipv4_address:
  type: str
  description:
     - IPv4 address of the server on the private network.
     - May be absent.
  returned: on success

public_ipv4_address:
  type: str
  description:
     - IPv4 address of the server on the public (internet) network.
     - May be absent.
  returned: on success

lease_start_at:
  type: str
  description:
     - Date when server lease started.
     - May be absent.
  returned: on success

scheduled_release_at:
   type: str
   description:
      - Date when server lease is planned for termination.
      - May be absent.
   returned: on success

configuration_details:
   type: complex
   description:
     - Structured server configuration
   contains:
     ram_size:
       type: int
       description:
         - server RAM.
         - May be absent.
     server_model_id:
       type: str
       description:
         - Internal ID of the server model.
         - May be absent.
     bandwidth_id:
       type: str
       description:
         - ID of the bandwidth accounting item associated with server.
         - May be absent.
     bandwidth_name:
       type: str
       description:
          - Name of the bandwidth accounting item associated with server.
          - May be absent.
     private_uplink_id:
       type: str
       description:
         - ID of the server uplink in the private network.
         - May be absent.
     private_uplink_name:
       type: str
       description:
         - Name of the server uplink in the private network.
         - May be absent.
     public_uplink_id:
       type: str
       description:
         - ID of the server uplink in the public network.
         - May be absent.
     public_uplink_name:
       type: str
       description:
         - Name of the server uplink in the public network.
         - May be absent.
     operating_system_id:
       type: str
       description:
         - ID of the installed OS on the server.
         - May be absent.
     operating_system_full_name:
       type: str
       description:
         - Name of the installed OS on the server.
         - May be absent.
   returned: on success

created_at:
  type: str
  description:
    - Date the server object was created in database.
  returned: on success

updated_at:
  type: str
  description:
    - Last date when the server object was updated.
  returned: on success

found:
  type: bool
  description:
    - Set to true if server is found.
    - Set to false if server is not found and I(can_be_absent)=C(true)
  returned: on success

ready:
  type: bool
  description:
    - Synthetic attribute, created by module.
    - Set to true if server is in status=active, power_status=powered_on,
      operational_status=normal.
  returned: on success
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


class APIError404(APIError):
    pass


class API(object):
    def __init__(self, endpoint, token):
        self.endpoint = endpoint
        self.token = token

    def start_request(self, path, query):
        req = requests.Request('GET', self.endpoint + path, params=query)
        req.headers['Authorization'] = f'Bearer {self.token}'
        return req

    def send_and_decode(self, request):
        session = requests.Session()
        prep_request = request.prepare()
        response = session.send(prep_request)
        if response.status_code == 401:
            raise APIError(
                msg='401 Unauthorized. Check if token is valid.',
                status_code=response.status_code,
                api_url=prep_request.url
            )
        if response.status_code == 404:
            raise APIError404(
                msg='404 Not Found.',
                status_code=response.status_code,
                api_url=prep_request.url
            )

        if response.status_code != 200:
            raise APIError(
                msg=f'API Error: {response.content }',
                status_code=response.status_code,
                api_url=prep_request.url
            )
        try:
            decoded = response.json()
        except ValueError as e:
            raise APIError(
                msg=f'API decoding error: {str(e)}, data: {response.content}',
                status_code=response.status_code,
                api_url=prep_request.url
            )
        return decoded


class SC_Dedicated_Server_Info(object):
    def __init__(self, endpoint, token, name, fail_on_absent):
        self.API = API(endpoint, token)
        self.server_id = name
        self.fail_on_absent = fail_on_absent

    @staticmethod
    def _is_server_ready(server_info):
        if (
            server_info.get('status') == 'active' and
            server_info.get('power_status') == 'powered_on' and
            server_info.get('operational_status') == 'normal'
        ):
            return True
        else:
            return False

    def run(self):
        req = self.API.start_request(
            path=f'/hosts/dedicated_servers/{self.server_id}',
            query=None
        )
        try:
            server_info = self.API.send_and_decode(req)
        except APIError404 as e:
            if self.fail_on_absent:
                raise e
            return {
                'changed': False,
                'found': False,
                'ready': False
            }
        module_output = server_info
        module_output['found'] = True
        module_output['ready'] = self._is_server_ready(server_info)
        module_output['changed'] = False
        return module_output


def main():
    module = AnsibleModule(
        argument_spec={
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'name': {'type': 'str', 'required': True, 'aliases': ['id']},
            'fail_on_absent': {'type': 'bool', 'default': True}
        },
        supports_check_mode=True
    )
    try:
        global requests
        import requests
    except Exception:
        module.exit_fail(msg='This module needs requests library.')
    sc_dedicated_server_info = SC_Dedicated_Server_Info(
        endpoint=module.params['endpoint'],
        token=module.params['token'],
        name=module.params['name'],
        fail_on_absent=module.params['fail_on_absent']
    )
    try:
        module.exit_json(**sc_dedicated_server_info.run())
    except APIError as e:
        module.exit_json(**e.fail())


if __name__ == '__main__':
    main()
