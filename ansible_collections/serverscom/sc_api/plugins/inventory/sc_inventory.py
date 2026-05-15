# Copyright (c) 2026 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
name: sc_inventory
version_added: "1.2.0"
author: "George Shuklin (@amarao)"
short_description: Servers.com dynamic inventory
description:
  - Builds Ansible inventory from the Servers.com API.
  - Fetches dedicated bare-metal servers, Scalable Bare-Metal (SBM) servers,
    Kubernetes bare-metal nodes, and cloud computing instances.
  - Supports filtering by kind, region, name regexp, labels, status, and
    arbitrary exclusion rules.
  - Hosts can be assigned to a static group or dynamically grouped by
    a server attribute.
options:
  plugin:
    description: Token that identifies the file as a config for this plugin.
    required: true
    choices: ['serverscom.sc_api.sc_inventory']
  token:
    description:
      - API bearer token for the Servers.com API.
      - If unset, the SERVERSCOM_API_TOKEN or SC_TOKEN environment variable is used.
    type: str
    required: false
    env:
      - name: SERVERSCOM_API_TOKEN
      - name: SC_TOKEN
  endpoint:
    description:
      - Base URL of the Servers.com API.
      - If unset, the SERVERSCOM_API_URL environment variable is used,
        falling back to the public endpoint.
    type: str
    required: false
    default: https://api.servers.com/v1
    env:
      - name: SERVERSCOM_API_URL
  resources:
    description:
      - List of resource blocks describing what to fetch and how to expose it.
      - If omitted or empty, every resource kind is fetched with no filters
        (via the bulk /hosts endpoint plus /cloud_computing/instances).
      - When at least one block is present, every block must specify C(kind).
    type: list
    elements: dict
    required: false
    default: []
    suboptions:
      kind:
        description:
          - Resource kind to fetch — required for every entry in C(resources).
          - One of C(baremetal), C(sbm), C(k8s_nodes), C(cloud).
          - To fetch every kind, omit C(resources) entirely (or set it to an
            empty list) instead of relying on per-block fallback.
        type: str
      regions:
        description:
          - List of location_code (baremetal) or region_code (cloud) values.
          - Empty list means all regions.
        type: list
        elements: str
        default: []
      name_regex:
        description: Regexp matched against the server title (baremetal) or name (cloud).
        type: str
      labels:
        description: Every key=value pair must be present on the server (AND match).
        type: dict
        default: {}
      status_filter:
        description: Status whitelist; empty means all statuses.
        type: list
        elements: str
        default: []
      exclude:
        description:
          - List of exclusion rules. A host is dropped if any rule matches.
          - A single rule matches when all its conditions hold.
        type: list
        elements: dict
        default: []
        suboptions:
          regions:
            description: Empty means any region.
            type: list
            elements: str
            default: []
          labels:
            description: Empty means no label test for this rule.
            type: dict
            default: {}
      ansible_host:
        description: Which IP field to expose as ansible_host.
        type: str
        choices: [public_ipv4, private_ipv4, public_ipv6, oob_ipv4, local_ipv4]
        default: public_ipv4
      assign_inventory_group:
        description:
          - Name of a static Ansible group to add every matched host into.
          - Mutually exclusive with group_by.
        type: str
      group_by:
        description:
          - Name of a top-level server attribute whose value becomes the group name.
          - Mutually exclusive with assign_inventory_group.
        type: str
      extra_vars:
        description: Constant variables set on every matched host (override raw fields).
        type: dict
        default: {}
"""

EXAMPLES = """
# 1. Everything — minimal config (no resources at all)
plugin: serverscom.sc_api.sc_inventory

---
# 2. All cloud instances, grouped by region
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: cloud
    group_by: region_code

---
# 3. All baremetal servers, grouped by location
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: baremetal
    group_by: location_code

---
# 4. Baremetal in specific regions only
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: baremetal
    regions: [AMS1, AMS7]
    assign_inventory_group: amsterdam_servers

---
# 5. Cloud filtered by label, using private IP
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: cloud
    labels:
      environment: staging
    ansible_host: private_ipv4
    status_filter: [ACTIVE]
    assign_inventory_group: staging
    extra_vars:
      ansible_user: ubuntu
      ansible_python_interpreter: /usr/bin/python3

---
# 6. Exclusion — all AMS1 servers except those labeled production
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: baremetal
    regions: [AMS1]
    exclude:
      - labels:
          environment: production
    assign_inventory_group: ams1_nonprod

---
# 7. Multi-rule exclusion — exclude AMS2 OR decommissioned
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: baremetal
    exclude:
      - regions: [AMS2]
      - labels: { decommissioned: "true" }
    assign_inventory_group: active_fleet

---
# 8. Environment variable substitution
# Usage: DEPLOY_REGION=AMS1 SC_ENV=production ansible-inventory -i dynamic.sc_api.yml --list
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: baremetal
    regions:
      - ${DEPLOY_REGION}
    labels:
      environment: ${SC_ENV}
    group_by: location_code

---
# 9. K8s nodes on private IPs
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: k8s_nodes
    ansible_host: private_ipv4
    assign_inventory_group: kubernetes_nodes
    extra_vars:
      ansible_user: root

---
# 10. Multiple kinds with different per-kind configs
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: baremetal
    regions: [AMS1, FRA1]
    labels: { managed: "true" }
    status_filter: [active]
    ansible_host: public_ipv4
    assign_inventory_group: baremetal_fleet
    extra_vars:
      ansible_user: root
  - kind: cloud
    regions: [AMS1, FRA1]
    labels: { managed: "true" }
    status_filter: [ACTIVE]
    ansible_host: public_ipv4
    group_by: region_code
    extra_vars:
      ansible_user: ubuntu
  - kind: k8s_nodes
    ansible_host: private_ipv4
    assign_inventory_group: k8s_nodes
    extra_vars:
      ansible_user: root

---
# 11. Name regexp — only hosts matching a pattern, across two kinds
plugin: serverscom.sc_api.sc_inventory
resources:
  - kind: cloud
    name_regex: "^web-"
    status_filter: [ACTIVE]
    assign_inventory_group: web_tier
  - kind: baremetal
    name_regex: "^web-"
    status_filter: [active]
    assign_inventory_group: web_tier
"""

import os
import re

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable
from ansible.utils.display import Display

from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    DEFAULT_API_ENDPOINT,
    SCBaseError,
    ScApi,
)

display = Display()

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_GROUP_NAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]")

_HOST_TYPE_TO_KIND = {
    "dedicated_server": "baremetal",
    "sbm_server": "sbm",
    "kubernetes_baremetal_node": "k8s_nodes",
}

_KIND_TO_HOST_TYPE = {
    "baremetal": "dedicated_server",
    "sbm": "sbm_server",
    "k8s_nodes": "kubernetes_baremetal_node",
}

_VALID_KINDS = {"baremetal", "sbm", "k8s_nodes", "cloud"}

_VALID_ANSIBLE_HOST = {
    "public_ipv4",
    "private_ipv4",
    "public_ipv6",
    "oob_ipv4",
    "local_ipv4",
}

# Strict key validation: any key not listed below is rejected at parse time.
_KNOWN_TOP_KEYS = {
    "plugin",
    "token",
    "endpoint",
    "resources",
    # inherited from Cacheable
    "cache",
    "cache_plugin",
    "cache_timeout",
    "cache_connection",
    "cache_prefix",
}

_KNOWN_BLOCK_KEYS = {
    "kind",
    "regions",
    "name_regex",
    "labels",
    "status_filter",
    "exclude",
    "ansible_host",
    "assign_inventory_group",
    "group_by",
    "extra_vars",
}

_KNOWN_EXCLUDE_RULE_KEYS = {"regions", "labels"}


class InventoryModule(BaseInventoryPlugin, Cacheable):

    NAME = "serverscom.sc_api.sc_inventory"

    # ------------------------------------------------------------------ #
    # Entry points
    # ------------------------------------------------------------------ #

    def verify_file(self, path):
        if not super(InventoryModule, self).verify_file(path):
            return False
        return path.endswith(
            (
                ".sc_api.yml",
                ".sc_api.yaml",
                ".sc_inventory.yml",
                ".sc_inventory.yaml",
            )
        )

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._reject_unknown_keys(loader, path)
        self._read_config_data(path)

        token, endpoint = self._resolve_token_endpoint()
        api = self._build_api(token, endpoint)

        resources = self.get_option("resources")

        try:
            if not resources:
                # No `resources:` (or empty list) → fetch every kind, no filters.
                self._apply_resource(api, {})
                return

            for raw_block in resources:
                block = self._substitute_env_vars(raw_block or {})
                if not block.get("kind"):
                    raise AnsibleParserError(
                        "Every entry in `resources:` must specify `kind` "
                        "(one of baremetal/sbm/k8s_nodes/cloud). "
                        "To fetch all kinds, omit `resources:` entirely "
                        "or set it to an empty list."
                    )
                self._apply_resource(api, block)
        except SCBaseError as e:
            raise AnsibleError(e.msg)

    # ------------------------------------------------------------------ #
    # Strict key validation
    # ------------------------------------------------------------------ #

    def _reject_unknown_keys(self, loader, path):
        """Raise AnsibleParserError if the config file contains any key
        not listed in the plugin's schema. Ansible's own validator is
        lenient and silently drops unknowns, which lets typos slip past;
        this restores strict behavior."""
        raw = loader.load_from_file(path, cache="none", unsafe=True)
        if not isinstance(raw, dict):
            raise AnsibleParserError(
                "Inventory config %r must be a YAML mapping." % path
            )

        extras = set(raw.keys()) - _KNOWN_TOP_KEYS
        if extras:
            raise AnsibleParserError(
                "Unknown top-level keys in %s: %s. Known keys: %s"
                % (path, sorted(extras), sorted(_KNOWN_TOP_KEYS))
            )

        for i, block in enumerate(raw.get("resources") or []):
            if not isinstance(block, dict):
                continue
            block_extras = set(block.keys()) - _KNOWN_BLOCK_KEYS
            if block_extras:
                raise AnsibleParserError(
                    "Unknown keys in resources[%d] of %s: %s. Known keys: %s"
                    % (i, path, sorted(block_extras), sorted(_KNOWN_BLOCK_KEYS))
                )
            for j, rule in enumerate(block.get("exclude") or []):
                if not isinstance(rule, dict):
                    continue
                rule_extras = set(rule.keys()) - _KNOWN_EXCLUDE_RULE_KEYS
                if rule_extras:
                    raise AnsibleParserError(
                        "Unknown keys in resources[%d].exclude[%d] of %s: %s"
                        % (i, j, path, sorted(rule_extras))
                    )

    # ------------------------------------------------------------------ #
    # Token / endpoint / api
    # ------------------------------------------------------------------ #

    def _resolve_token_endpoint(self):
        token = self.get_option("token")
        if not token:
            token = os.environ.get("SERVERSCOM_API_TOKEN") or os.environ.get(
                "SC_TOKEN"
            )
        if token:
            token = self._substitute_env_vars(token)
        if not token:
            raise AnsibleError(
                "No API token found. Set SERVERSCOM_API_TOKEN or SC_TOKEN "
                "environment variable, or pass 'token:' in the inventory config."
            )

        endpoint = self.get_option("endpoint")
        if not endpoint:
            endpoint = os.environ.get("SERVERSCOM_API_URL", DEFAULT_API_ENDPOINT)
        endpoint = self._substitute_env_vars(endpoint)
        return token, endpoint

    def _build_api(self, token, endpoint):
        return ScApi(token, endpoint)

    # ------------------------------------------------------------------ #
    # ${VAR} substitution
    # ------------------------------------------------------------------ #

    def _substitute_env_vars(self, value):
        if isinstance(value, str):
            def replace(match):
                name = match.group(1)
                resolved = os.environ.get(name)
                if resolved is None:
                    raise AnsibleParserError(
                        "Environment variable %r referenced in inventory "
                        "config is not set." % name
                    )
                return resolved

            return _ENV_VAR_RE.sub(replace, value)
        if isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]
        if isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}
        return value

    # ------------------------------------------------------------------ #
    # Listing / kind dispatch
    # ------------------------------------------------------------------ #

    def _list_for_kind(self, api, kind):
        if kind is None:
            for host in api.list_hosts():
                mapped = _HOST_TYPE_TO_KIND.get(host.get("type"))
                if mapped is None:
                    display.warning(
                        "Skipping host id=%r with unknown type=%r"
                        % (host.get("id"), host.get("type"))
                    )
                    continue
                yield host, mapped
            for instance in api.list_instances():
                yield instance, "cloud"
            return

        if kind not in _VALID_KINDS:
            raise AnsibleParserError(
                "Unknown resource kind %r; valid: %s"
                % (kind, sorted(_VALID_KINDS))
            )

        if kind == "cloud":
            for instance in api.list_instances():
                yield instance, "cloud"
            return

        host_type = _KIND_TO_HOST_TYPE[kind]
        for host in api.list_hosts(type=host_type):
            yield host, kind

    # ------------------------------------------------------------------ #
    # Per-host accessors
    # ------------------------------------------------------------------ #

    def _hostname(self, server, kind):
        field = "name" if kind == "cloud" else "title"
        name = server.get(field)
        if not name:
            server_id = server.get("id")
            display.warning(
                "Server id=%r has empty %s; falling back to id as hostname."
                % (server_id, field)
            )
            return str(server_id) if server_id is not None else None
        return name

    def _region(self, server, kind):
        if kind == "cloud":
            return server.get("region_code")
        return server.get("location_code")

    def _ip(self, server, kind, ip_type):
        if ip_type == "public_ipv4":
            return server.get("public_ipv4_address")
        if ip_type == "private_ipv4":
            return server.get("private_ipv4_address")
        if ip_type == "public_ipv6":
            if kind == "cloud":
                return server.get("public_ipv6_address")
            return None
        if ip_type == "oob_ipv4":
            if kind == "baremetal":
                return server.get("oob_ipv4_address")
            return None
        if ip_type == "local_ipv4":
            if kind == "cloud":
                return server.get("local_ipv4_address")
            return None
        return None

    # ------------------------------------------------------------------ #
    # Filtering
    # ------------------------------------------------------------------ #

    def _matches_labels(self, host_labels, required):
        if not required:
            return True
        if not isinstance(host_labels, dict):
            return False
        for k, v in required.items():
            if host_labels.get(k) != v:
                return False
        return True

    def _is_excluded(self, server, kind, exclude_rules):
        if not exclude_rules:
            return False
        region = self._region(server, kind)
        host_labels = server.get("labels") or {}
        for rule in exclude_rules:
            rule = rule or {}
            rule_regions = rule.get("regions") or []
            rule_labels = rule.get("labels") or {}
            region_ok = (not rule_regions) or (region in rule_regions)
            labels_ok = self._matches_labels(host_labels, rule_labels)
            if region_ok and labels_ok:
                return True
        return False

    # ------------------------------------------------------------------ #
    # Grouping
    # ------------------------------------------------------------------ #

    def _sanitize_group(self, name):
        return _GROUP_NAME_SANITIZE_RE.sub("_", str(name))

    def _add_to_groups(self, hostname, server, assign_inventory_group, group_by):
        if assign_inventory_group and group_by:
            raise AnsibleParserError(
                "assign_inventory_group and group_by are mutually exclusive "
                "within a single resource block."
            )
        if assign_inventory_group:
            group = self._sanitize_group(assign_inventory_group)
            self.inventory.add_group(group)
            self.inventory.add_child(group, hostname)
        elif group_by:
            value = server.get(group_by)
            if value in (None, ""):
                display.warning(
                    "Host %r: group_by attribute %r is missing/empty; "
                    "not added to any extra group."
                    % (hostname, group_by)
                )
                return
            group = self._sanitize_group(value)
            self.inventory.add_group(group)
            self.inventory.add_child(group, hostname)

    # ------------------------------------------------------------------ #
    # Host variables
    # ------------------------------------------------------------------ #

    def _set_host_vars(
        self, hostname, server, kind, ansible_host_type, extra_vars
    ):
        ip = self._ip(server, kind, ansible_host_type)
        if ip:
            self.inventory.set_variable(hostname, "ansible_host", ip)
        else:
            display.warning(
                "Host %r: configured ansible_host=%s is not available; "
                "host added without ansible_host."
                % (hostname, ansible_host_type)
            )

        self.inventory.set_variable(
            hostname, "public_ip", server.get("public_ipv4_address")
        )
        self.inventory.set_variable(
            hostname, "private_ip", server.get("private_ipv4_address")
        )
        self.inventory.set_variable(
            hostname,
            "public_ipv6",
            server.get("public_ipv6_address") if kind == "cloud" else None,
        )
        self.inventory.set_variable(
            hostname,
            "oob_ip",
            server.get("oob_ipv4_address") if kind == "baremetal" else None,
        )
        self.inventory.set_variable(
            hostname,
            "local_ip",
            server.get("local_ipv4_address") if kind == "cloud" else None,
        )
        self.inventory.set_variable(hostname, "additional_ip_addresses", [])
        self.inventory.set_variable(hostname, "sc_kind", kind)

        for key, value in server.items():
            self.inventory.set_variable(hostname, key, value)

        for key, value in (extra_vars or {}).items():
            self.inventory.set_variable(hostname, key, value)

    # ------------------------------------------------------------------ #
    # Main per-resource flow
    # ------------------------------------------------------------------ #

    def _apply_resource(self, api, config):
        kind = config.get("kind")
        regions = config.get("regions") or []
        name_regex = config.get("name_regex")
        labels = config.get("labels") or {}
        status_filter = config.get("status_filter") or []
        exclude_rules = config.get("exclude") or []
        ansible_host_type = config.get("ansible_host") or "public_ipv4"
        if ansible_host_type not in _VALID_ANSIBLE_HOST:
            raise AnsibleParserError(
                "Invalid ansible_host=%r; valid: %s"
                % (ansible_host_type, sorted(_VALID_ANSIBLE_HOST))
            )
        assign_inventory_group = config.get("assign_inventory_group")
        group_by = config.get("group_by")
        if assign_inventory_group and group_by:
            raise AnsibleParserError(
                "assign_inventory_group and group_by are mutually exclusive "
                "within a single resource block."
            )
        extra_vars = config.get("extra_vars") or {}

        compiled_regex = re.compile(name_regex) if name_regex else None

        for server, server_kind in self._list_for_kind(api, kind):
            region = self._region(server, server_kind)
            if regions and region not in regions:
                continue

            hostname = self._hostname(server, server_kind)
            if not hostname:
                continue
            if compiled_regex and not compiled_regex.search(hostname):
                continue

            if labels and not self._matches_labels(
                server.get("labels") or {}, labels
            ):
                continue

            if status_filter and server.get("status") not in status_filter:
                continue

            if self._is_excluded(server, server_kind, exclude_rules):
                continue

            self.inventory.add_host(hostname)
            self._set_host_vars(
                hostname, server, server_kind, ansible_host_type, extra_vars
            )
            self._add_to_groups(
                hostname, server, assign_inventory_group, group_by
            )
