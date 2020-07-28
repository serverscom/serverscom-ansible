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
limits:
    description:
        - Limits for API use (extraced from headers)
    type: complex
    returned: on success
    contains:
        limit:
            type: int
            description:
              - Total limit for requests.
              - Corresponds to X-RateLimit-Limit header of API reply.
        remaining:
            type: int
            description:
              - Remaining limit for requests.
              - Corresponds to X-RateLimit-Remaining header of API reply.
              - Causes warning if value is 0.
        reset:
            type: int
            description:
                - timestamp for the next limit reset.
                - Corresponds to X-RateLimit-Reset header of API reply.

locations:
    description:
        - List of locations for baremetal servers
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
