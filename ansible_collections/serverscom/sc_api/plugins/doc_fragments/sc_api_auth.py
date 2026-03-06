# -*- coding: utf-8 -*-
# (c) 2020, Servers.com
# GNU General Public License v3.0
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
    endpoint:
      type: str
      default: https://api.servers.com/v1
      description:
        - Endpoint to use to connect to API.
        - Do not change until specifically asked to do otherwise.
        - If not set, the value of the C(SERVERSCOM_API_URL) environment variable is used.

    token:
      type: str
      required: true
      description:
        - Token to use.
        - You can create token for your account in https://portal.servers.com
          in Profile -> Public API section.
        - If not set, the value of the C(SERVERSCOM_API_TOKEN) or C(SC_TOKEN) environment variable is used
          (C(SERVERSCOM_API_TOKEN) takes precedence).
        - Value is not logged.
"""
