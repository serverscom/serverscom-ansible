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
module: bgp_group
version_added: "1.3.0"
author: "Servers.com Team (@serverscom)"
short_description: Create, update or delete BGP groups
description: >
    Create, update or delete a BGP group. A BGP group is a set of hosts
    (servers) in one or more locations which establish BGP sessions and
    announce permitted prefixes.
notes:
    - BGP must be enabled for the account, otherwise the API returns 403.
    - >
      The group is updated only when it is C(active). If the group is
      C(pending) and changes are needed, the module waits for it to become
      C(active) (or fails if I(wait=0)). Groups in C(failed) or C(removing)
      status can't be updated.
    - >
      A prefix requested by I(mask) is allocated by the API, its address
      is known only after allocation. To make the playbook refer to that
      specific prefix later, pin it by I(prefix) or I(id).
extends_documentation_fragment: serverscom.sc_api.api_auth

options:
    state:
      type: str
      default: present
      choices: [present, absent]
      description:
        - Desired state of the BGP group.
        - C(present) creates the group or updates the existing one.
        - C(absent) deletes the group.

    bgp_group_id:
      type: str
      description:
        - ID of an existing BGP group.
        - If the group is not found, the module fails (groups are never
          created by id).
        - If both I(bgp_group_id) and I(name) are set, the group is
          renamed to I(name).
        - At least one of I(bgp_group_id) or I(name) is required.

    name:
      type: str
      description:
        - Name of the BGP group. Names are unique within the account.
        - Used to find the group if I(bgp_group_id) is not set.
        - At least one of I(bgp_group_id) or I(name) is required.

    network_type:
      type: str
      choices: [public]
      description:
        - Network type of the group.
        - Used only for creation, defaults to C(public). Can't be changed.

    asn:
      type: int
      description:
        - Customer's ASN for eBGP session.
        - Omit for iBGP.
        - Used only for creation. Can't be changed. If omitted for an
          existing group, it is not checked.

    location_ids:
      type: list
      elements: int
      description:
        - IDs of locations of the group.
        - Required for creation (or I(location_codes)).
        - If omitted for an existing group, locations are not changed.
        - Mutually exclusive with I(location_codes).

    location_codes:
      type: list
      elements: str
      description:
        - Codes of locations of the group (for example, C(AMS1)).
        - Mutually exclusive with I(location_ids).

    hosts:
      type: list
      elements: dict
      description:
        - Hosts (servers) of the group. Up to 8 hosts.
        - Required for creation.
        - Replaces the full list of hosts of an existing group.
        - If omitted for an existing group, hosts are not changed.
      suboptions:
        server_id:
          type: str
          description:
            - ID of the server.
            - Mutually exclusive with I(hostname).
        hostname:
          type: str
          description:
            - Hostname of the server (exact match on the host title).
            - Mutually exclusive with I(server_id).

    announced_prefixes:
      type: list
      elements: dict
      description:
        - Desired announced prefixes of the group. Up to 4 prefixes.
        - Each item is one prefix and must have exactly one of I(mask),
          I(prefix) or I(id).
        - Items with I(mask) are matched by count against existing
          prefixes with the same mask, missing prefixes are requested.
        - Items with I(prefix) pin the existing prefix with this address.
          If the group has no such prefix, it is requested, and the API
          decides whether it is permitted.
        - Items with I(id) pin an existing prefix. They can't be used to
          request a new prefix.
        - Existing prefixes not matched by any item are kept unless
          I(prune_prefixes) is set.
        - Prefixes in C(removing) status are ignored.
        - Prefixes in any other status (including C(failed) and C(blocked))
          count as existing and satisfy I(mask) items. To replace a failed
          prefix, first remove it (list the other prefixes pinned by
          I(prefix) or I(id) and set I(prune_prefixes)), then request a new
          one by I(mask).
        - If omitted, prefixes are not changed.
      suboptions:
        mask:
          type: int
          choices: [26, 27, 28, 29, 30, 31, 32]
          description:
            - Mask of the requested prefix.
        prefix:
          type: str
          description:
            - Prefix in CIDR notation (for example, C(192.0.2.0/29)).
            - Host bits must be zero.
        id:
          type: str
          description:
            - ID of the existing prefix.

    prune_prefixes:
      type: bool
      default: false
      description:
        - Remove existing prefixes not matched by I(announced_prefixes).
        - Removed prefixes are no longer announced. A prefix allocated by
          I(mask) is released, requesting it again gives a different
          address.
        - If there are more existing unpinned prefixes of some mask than
          requested, the module fails instead of guessing which ones to
          remove. Pin prefixes to keep by I(prefix) or I(id).
        - Has no effect if I(announced_prefixes) is omitted.

    labels:
      type: dict
      description:
        - Labels of the group. Replaces existing labels.
        - If omitted, labels are not changed.
        - Use an empty dict to remove all labels.

    wait:
      type: int
      default: 600
      description:
        - Maximum time in seconds to wait for the group to become
          C(active) (with no pending prefixes) after creation or update,
          or to disappear after deletion.
        - Also used to wait for a C(pending) group to become C(active)
          before update or deletion.
        - Set to 0 to not wait.

    update_interval:
      type: int
      default: 5
      description:
        - Interval in seconds between status checks.
"""

RETURN = """
bgp_group:
  type: dict
  returned: on success
  description:
    - BGP group.
    - Empty dict if I(state=absent).
    - In check mode, the expected state of the group (with C(id=None)
      for a new group).
  contains:
    id:
      type: str
      description: ID of the BGP group.
    name:
      type: str
      description: Name of the BGP group.
    network_type:
      type: str
      description: Network type (C(public) or C(private)).
    asn:
      type: int
      description: Session ASN.
    session_type:
      type: str
      description: Session type (C(ibgp) or C(ebgp)).
    status:
      type: str
      description: Group status (C(pending), C(active), C(removing), C(failed)).
    location_ids:
      type: list
      elements: int
      description: Location IDs of the group.
    hosts:
      type: list
      elements: dict
      description: Hosts of the group (C(server_id), C(location_id)).
    announced_prefixes:
      type: list
      elements: dict
      description:
        - Announced prefixes of the group (C(id), C(prefix), C(mask),
          C(quantity), C(status), C(created_at)).
        - Prefix status is one of C(pending), C(active), C(removing),
          C(blocked), C(failed).
    max_prefix_limit:
      type: int
      description: Maximum prefix limit (may be null).
    labels:
      type: dict
      description: Labels of the group.
    created_at:
      type: str
      description: Creation time.
    updated_at:
      type: str
      description: Last update time.

prefixes_added:
  type: list
  elements: dict
  returned: if I(state=present)
  description:
    - "Requested new prefixes, each is C({mask: N}) or C({prefix: CIDR})."

prefixes_removed:
  type: list
  elements: dict
  returned: if I(state=present)
  description: Prefixes removed because of I(prune_prefixes).

api_url:
  type: str
  returned: on failure
  description: URL for the failed request.

status_code:
  type: int
  returned: on failure
  description: Status code for the request.
"""

EXAMPLES = """
- name: Create iBGP group with two hosts and one /29 prefix
  serverscom.sc_api.bgp_group:
    token: '{{ sc_token }}'
    name: bgp-1
    location_codes: [AMS1]
    hosts:
      - hostname: web-01
      - server_id: X7axylby
    announced_prefixes:
      - mask: 29
  register: bgp

- name: Create eBGP group with customer's ASN
  serverscom.sc_api.bgp_group:
    token: '{{ sc_token }}'
    name: bgp-ebgp
    asn: 64512
    location_ids: [1]
    hosts:
      - server_id: LDdwxre1

- name: Add one more /29 prefix, keeping the first one pinned
  serverscom.sc_api.bgp_group:
    token: '{{ sc_token }}'
    name: bgp-1
    announced_prefixes:
      - prefix: '{{ bgp.bgp_group.announced_prefixes[0].prefix }}'
      - mask: 29

- name: Keep only the pinned prefix, remove the rest
  serverscom.sc_api.bgp_group:
    token: '{{ sc_token }}'
    name: bgp-1
    announced_prefixes:
      - prefix: 100.64.128.0/29
    prune_prefixes: true

- name: Rename group and update labels
  serverscom.sc_api.bgp_group:
    token: '{{ sc_token }}'
    bgp_group_id: y5eVOMaE
    name: bgp-renamed
    labels:
      env: prod

- name: Delete group
  serverscom.sc_api.bgp_group:
    token: '{{ sc_token }}'
    name: bgp-1
    state: absent
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    AUTH_ARGS,
    SCBaseError,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.bgp import (
    ScBgpGroup,
)


def main():
    module = AnsibleModule(
        argument_spec={
            **AUTH_ARGS,
            "state": {
                "type": "str",
                "default": "present",
                "choices": ["present", "absent"],
            },
            "bgp_group_id": {"type": "str"},
            "name": {"type": "str"},
            "network_type": {"type": "str", "choices": ["public"]},
            "asn": {"type": "int"},
            "location_ids": {"type": "list", "elements": "int"},
            "location_codes": {"type": "list", "elements": "str"},
            "hosts": {
                "type": "list",
                "elements": "dict",
                "options": {
                    "server_id": {"type": "str"},
                    "hostname": {"type": "str"},
                },
                "mutually_exclusive": [["server_id", "hostname"]],
                "required_one_of": [["server_id", "hostname"]],
            },
            "announced_prefixes": {
                "type": "list",
                "elements": "dict",
                "options": {
                    "mask": {"type": "int", "choices": [26, 27, 28, 29, 30, 31, 32]},
                    "prefix": {"type": "str"},
                    "id": {"type": "str"},
                },
                "mutually_exclusive": [["mask", "prefix", "id"]],
                "required_one_of": [["mask", "prefix", "id"]],
            },
            "prune_prefixes": {"type": "bool", "default": False},
            "labels": {"type": "dict"},
            "wait": {"type": "int", "default": 600},
            "update_interval": {"type": "int", "default": 5},
        },
        required_one_of=[["bgp_group_id", "name"]],
        mutually_exclusive=[["location_ids", "location_codes"]],
        supports_check_mode=True,
    )
    try:
        bgp_group = ScBgpGroup(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            state=module.params["state"],
            bgp_group_id=module.params["bgp_group_id"],
            name=module.params["name"],
            network_type=module.params["network_type"],
            asn=module.params["asn"],
            location_ids=module.params["location_ids"],
            location_codes=module.params["location_codes"],
            hosts=module.params["hosts"],
            announced_prefixes=module.params["announced_prefixes"],
            prune_prefixes=module.params["prune_prefixes"],
            labels=module.params["labels"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            checkmode=module.check_mode,
        )
        module.exit_json(**bgp_group.run())
    except SCBaseError as e:
        module.fail_json(**e.fail())


if __name__ == "__main__":
    main()
