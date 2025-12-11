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
        choices: [raid1-simple, raid0-simple, no-raid]
        description:
            - Mutually exclusive with I(drives_layout).
            - Provides a template to use instead of I(drives_layout).
            - C(raid1-simple) uses two first drives to create RAID1,
              partition /boot (1Gb), swap (4Gb) and / (all other space).
            - C(raid0-simple) uses first two drives to create RAID0,
              partition /boot (1Gb), swap (4Gb) and / (all other space).
            - C(no-raid) uses first drive, does not create any RAID,
              partition /boot (1Gb), swap (4Gb) and / (all other space).
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
        - Mutually exclusive with I(operating_system_regex).

    operating_system_regex:
      type: str
      description:
        - Regular expression to filter operating systems by name.
        - If specified, the module will install operating system
          that match the provided regex (case insensitive).
        - Mutually exclusive with I(operating_system_id).

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
id:
  type: str
  description:
    - Unique identifier of the server.
  returned: on success

title:
  type: str
  description:
    - Display name of the server.
  returned: on success

type:
  type: str
  description:
    - Always 'dedicated_server'.
  returned: on success

rack_id:
  type: str
  description:
    - Identifier of the rack where the server is deployed.
    - Null during provisioning.
  returned: on success

status:
  type: str
  description:
    - "init: ordered but not provisioned;"
    - "pending: running operation;"
    - "active: ready to use."
  returned: on success

operational_status:
  type: str
  description:
    - "Detailed operation state."
    - "normal: there are no operations on a server, but
      this status doesn't guarantee accessibility by SSH."
    - "maintenance: server in maintanence mode."
    - "provisioning: a server is being activated after an order."
    - "installation: this status is displayed while OS reinstalling."
    - "entering_rescue_mode, rescue_mode, exiting_rescue_mode: these
      statuses show rescue mode progress."
  returned: on success

power_status:
  type: str
  description:
    - "unknown: this status is displayed while the server's provisioning
      or in a case when something went wrong;"
    - "powering_on: transitional status between power off and on;"
    - "powered_on: power is on;"
    - "powering_off: transitional status between power on and off;"
    - "powered_off: power is off;"
    - "power_cycling: power reboot."
  returned: on success

configuration:
  type: str
  description:
    - Chassis model, RAM and disk info.
  returned: on success

location_id:
  type: int
  description:
    - Identifier of the server location.
  returned: on success

location_code:
  type: str
  description:
    - Technical code of the location.
  returned: on success

private_ipv4_address:
  type: str
  description:
    - Private-network IPv4.
    - May be null.
  returned: on success

public_ipv4_address:
  type: str
  description:
    - Public-network IPv4.
    - May be null.
  returned: on success

oob_ipv4_address:
  type: str
  description:
    - Out-of-band IPv4 when enabled.
    - May be null.
  returned: on success

lease_start_at:
  type: str
  description:
    - Lease start date.
    - May be null.
  returned: on success

scheduled_release_at:
  type: str
  description:
    - Scheduled release date-time.
    - May be null.
  returned: on success

configuration_details:
  type: complex
  description:
    - Structured server configuration.
  contains:
    ram_size:
      type: int
      description:
        - RAM size in MB.
        - May be null.
    server_model_id:
      type: int
      description:
        - Identifier of the server model.
        - May be null.
    server_model_name:
      type: str
      description:
        - Human-readable server model name.
        - May be null.
    bandwidth_id:
      type: int
      description:
        - Identifier of bandwidth option.
        - May be null.
    bandwidth_name:
      type: str
      description:
        - Name of bandwidth option.
        - May be null.
    private_uplink_id:
      type: int
      description:
        - Identifier of private uplink.
        - May be null.
    private_uplink_name:
      type: str
      description:
        - Name of private uplink.
        - May be null.
    public_uplink_id:
      type: int
      description:
        - Identifier of public uplink.
        - May be null.
    public_uplink_name:
      type: str
      description:
        - Name of public uplink.
        - May be null.
    operating_system_id:
      type: int
      description:
        - Identifier of installed OS.
        - May be null.
    operating_system_full_name:
      type: str
      description:
        - Full name of installed OS.
        - May be null.
  returned: on success

labels:
  type: dict
  description:
    - Labels attached to the server.
  returned: on success

created_at:
  type: str
  description:
    - Creation timestamp.
  returned: on success

updated_at:
  type: str
  description:
    - Last update timestamp.
  returned: on success

found:
  type: bool
  description:
    - True if server exists; false if absent and can_be_absent is true.
  returned: on success

ready:
  type: bool
  description:
    - True when status='active', power_status='powered_on', operational_status='normal'.
  returned: on success
"""

EXAMPLES = """
- name: Server reinstallation
  sc_dedicated_server_reinstall:
    token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MzgxMjEsInR5cGUiOiJVc2VyIiwiYWNjZXNzX2dyYW50X2lkIjoyNjgwNywiZXhwIjoyMjI2OTk3NjMwfQ.rO4nGXNgXggjNmMJBLXovOh1coNrDWl4dGrGFupYXJE'
    id: 'lxyeQG8Q'
    drives_layout_template: raid1-simple
    operating_system_id: 49
    hostname: reinstall
    wait: 0
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
                "choices": ["raid1-simple", "raid0-simple", "no-raid"],
            },
            "drives_layout": {"type": "list", "elements": "dict"},
            "operating_system_id": {"type": "int"},
            "operating_system_regex": {"type": "str"},
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
            ["operating_system_id", "operating_system_regex"],
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
            operating_system_regex=module.params["operating_system_regex"],
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
