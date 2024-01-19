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
module: sc_dedicated_server_reinstall
version_added: "1.0.0"
author: "George Shuklin (@amarao)"
short_description: Reinstall baremetal server.
description: >
    Reinstall the existing baremetal server. Existing data may be lost in
    the process. No secure erase or wipe is performed during installation.
    Some data may be preserved.
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

    server_id:
      aliases: [name, id]
      type: str
      required: true
      description:
        - ID of the server to reinstall.

    hostname:
      type: str
      description:
        - Hostname for the server.
        - Module will retrive old server title if not specified.
        - Translates to hostname in API.

    drives_layout_template:
        type: str
        choices: [raid1-simple, raid0-simple]
        description:
            - Mutually exclusive with I(drives_layout).
            - Provides a template to use instead of I(drives_layout).
            - C(raid1-simple) uses two first drives to create RAID1,
              partition /boot (1Gb), swap (4Gb) and / (all other space).
            - C(raid0-simple) uses first drive as raid0 (or no raid in case
              of servers without hardware raid), and places /boot, swap
              and / on this drive.
            - This option is implemented by this module (it generates layout
              for drives['layout'] request to API based on built-in template).

    drives_layout:
      type: list
      elements: dict
      description:
        - Partitioning schema for drives during reinstallation.
        - Mutually exclusive with I(drives_layout_template).
        - Translates to drives["layout"] in API.
        - List of configuration for each raid or a stand-alone drive.
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
      type: int
      description:
        - id of the operating system to install on the server.
        - Module will retrive and reuse old operating system if
          not specified.

    ssh_keys:
      type: list
      elements: str
      description:
        - Array of fingerprints of public ssh keys to add for root user.
        - Keys must be registered before use by module M(serverscom.sc_api.sc_ssh_key).
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
              Use M(serverscom.sc_api.wait_for_connection) module
              to wait the server to become available though ssh.
            - Installation may start few minutes later than request,
              during this time server is responding with 'old' ssh.

    update_interval:
        type: int
        default: 60
        description:
            - Interval in seconds for requests for server status.
            - Each update request reduces number of available API
              requests in accordance with ratelimit.
            - Minimal value is 10.
            - Ignored if I(wait)=C(0).

    user_data:
      type: str
      description:
        - User data content that will be processed by the cloud-init
          while server's initialization.
"""

RETURN = """

"""

EXAMPLES = """

"""  # noqa


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScDedicatedServerReinstall,
)


__metaclass__ = type


def main():
    module = AnsibleModule(
        argument_spec={
            "token": {"type": "str", "no_log": True, "required": True},
            "endpoint": {"default": DEFAULT_API_ENDPOINT},
            "server_id": {"type": "str", "required": True, "aliases": ["id", "name"]},
            "hostname": {"type": "str"},
            "drives_layout_template": {
                "type": "str",
                "choices": ["raid1-simple", "raid0-simple"],
            },
            "drives_layout": {"type": "list", "elements": "dict"},
            "operating_system_id": {"type": "int"},
            "ssh_keys": {"type": "list", "elements": "str", "no_log": False},
            "ssh_key_name": {"type": "str"},
            "wait": {"type": "int", "default": 86400},
            "update_interval": {"type": "int", "default": 60},
            "user_data": {"type": "str"},
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ["ssh_keys", "ssh_key_name"],
            ["drives_layout", "drives_layout_template"],
        ],
        required_one_of=[["drives_layout", "drives_layout_template"]],
    )
    try:
        sc_dedicated_server_reinstall = ScDedicatedServerReinstall(
            endpoint=module.params["endpoint"],
            token=module.params["token"],
            server_id=module.params["server_id"],
            hostname=module.params["hostname"],
            drives_layout_template=module.params["drives_layout_template"],
            drives_layout=module.params["drives_layout"],
            operating_system_id=module.params["operating_system_id"],
            ssh_keys=module.params["ssh_keys"],
            ssh_key_name=module.params["ssh_key_name"],
            wait=module.params["wait"],
            update_interval=module.params["update_interval"],
            user_data=module.params["user_data"],
            checkmode=module.check_mode,
        )
        module.exit_json(**sc_dedicated_server_reinstall.run())
    except SCBaseError as e:
        module.exit_json(**e.fail())


if __name__ == "__main__":
    main()
