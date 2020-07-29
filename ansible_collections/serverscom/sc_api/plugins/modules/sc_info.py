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
module: sc_info
version_added: "2.10"
author: "George Shuklin (@amarao)"
short_description: Information about available locations and regions.
description: >
    Module gathers information about available locations
    for baremetal servers and cloud regions.

options:
    scope:
      type: str
      choices: [all, locations, regions]
      default: all
      description:
        - Scope of query
        - C(locations) limit query to baremetal locations
        - C(regions) limit query to cloud regions.
        - C(all) query both baremetal locations and cloud regions.

    search_pattern:
        type: str
        description:
            - Search substring in locations names.
            - Case insensitive.

    required_features:
        type: list
        description:
            - Filter locations based on features.
            - Seach both top-level features and supported_features.
            - If more than one element specified, search for all of them
              ('and' operation).
        elements: str

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
locations:
    description:
        - List of locations for baremetal servers
        - May contain additional flags for features for location
    returned: on success
    type: complex
    contains:
        id:
            type: str
            description:
                - ID of the location.
        name:
            type: str
            description:
                - Name of the location.

        code:
            type: str
            description:
                - Code for the location.

        supported_features:
            type: list
            description:
                - List of supported features
            example:
                - disaggregated_public_ports
                - disaggregated_private_ports
                - no_public_network
                - no_private_ip
                - host_rescue_mode
                - oob_public_access

regions:
    description: List of cloud compute regions
    returned: on success
    type: complex
    contains:
        id:
            type: str
            description:
                - ID of the location.
        name:
            type: str
            description:
                - Name of the location.

        code:
            type: str
            description:
                - Code for the location.
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
- name: Gather information for avaliable regions
  serverscom.sc_api.sc_info:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
  register: sc_info

- name: Print all locations
  debug: var=item.name
  with_items: '{{ sc_info.locations }}'

- name: Print all regions
  debug: var=item.name
  with_items: '{{ sc_info.regions }}'

- name: Print remaining API request count
  debug: var=sc_info.limits.remaining
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


class SC_Info(object):
    def __init__(self, endpoint, token, scope,
                 search_pattern, required_features):
        self.scope = scope
        self.search_pattern = search_pattern
        self.required_features = required_features
        self.API = API(endpoint, token)

    @staticmethod
    def location_features(location):
        features = set(location['supported_features'])
        for key, value in location.items():
            # fiter out both non-feature things like name, and
            # disabled features,
            if value is True:
                features.add(key)
        return features

    def locations(self):
        req = self.API.start_request(
            path='/locations',
            query={'search_pattern': self.search_pattern}
        )
        all_locations = list(itertools.chain.from_iterable(MultiPage(req)))
        locations = []
        if self.required_features:
            for loc in all_locations:
                feature_match = not (
                    set(self.required_features) - self.location_features(loc)
                )
                if feature_match:
                    locations.append(loc)

        else:
            locations = all_locations
        return locations

    def regions(self):
        req = self.API.start_request(
            path='/cloud_computing/regions',
            query={'search_pattern': self.search_pattern}
        )
        return list(itertools.chain.from_iterable(MultiPage(req)))

    def run(self):

        ret_data = {'changed': False}
        try:
            if self.scope in ['all', 'locations']:
                ret_data["locations"] = self.locations()
            if self.scope in ['all', 'regions']:
                ret_data["regions"] = self.regions()
        except APIError as e:
            return e.fail()

        return ret_data


def main():
    module = AnsibleModule(
        argument_spec={
            'scope': {
                'type': 'str',
                'choices': ['all', 'locations', 'regions'],
                'default': 'all'
            },
            'search_pattern': {'type': 'str'},
            'token': {'type': 'str', 'no_log': True, 'required': True},
            'endpoint': {'default': DEFAULT_API_ENDPOINT},
            'required_features': {'type': 'list'},
        },
        supports_check_mode=True
    )
    try:
        global requests
        import requests
    except Exception:
        module.exit_fail(msg='This module needs requests library.')
    sc_info = SC_Info(
        endpoint=module.params['endpoint'],
        token=module.params['token'],
        scope=module.params['scope'],
        search_pattern=module.params['search_pattern'],
        required_features=module.params['required_features'],
    )
    module.exit_json(**sc_info.run())


if __name__ == '__main__':
    main()
