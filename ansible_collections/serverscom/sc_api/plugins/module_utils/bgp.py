from __future__ import absolute_import, division, print_function
import ipaddress
import time

from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    APIError404,
    ScApi,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
    _retry_rules_for_wait,
)


__metaclass__ = type


DEFAULT_NETWORK_TYPE = "public"


def resolve_location_ids(api, location_ids=None, location_codes=None):
    """Resolve a list of location ids or a list of location codes.

    Returns a list of location ids without duplicates (order preserved),
    or None if neither is provided.
    """
    if location_ids and location_codes:
        raise ModuleError("location_ids and location_codes are mutually exclusive.")
    if location_ids is not None:
        return _dedup([int(location_id) for location_id in location_ids])
    if location_codes is None:
        return None
    wanted = _dedup([code.upper() for code in location_codes])
    found = {}
    for location in api.list_locations():
        code = (location.get("code") or "").upper()
        if code in wanted:
            found[code] = location["id"]
    missing = [code for code in wanted if code not in found]
    if missing:
        raise ModuleError(f"Location(s) with code(s) {', '.join(missing)} not found.")
    return [found[code] for code in wanted]


def resolve_host_id(api, server_id=None, hostname=None):
    """Resolve server_id or hostname (exact match on the host title)."""
    if server_id and hostname:
        raise ModuleError("server_id and hostname are mutually exclusive.")
    if not server_id and not hostname:
        raise ModuleError("One of server_id or hostname must be provided.")
    if server_id:
        return server_id
    found = [
        host["id"]
        for host in api.list_hosts(search_pattern=hostname)
        if host.get("title") == hostname
    ]
    if len(found) > 1:
        raise ModuleError(f"Multiple hosts found with hostname '{hostname}'.")
    if not found:
        raise ModuleError(f"Host with hostname '{hostname}' not found.")
    return found[0]


def resolve_host_ids(api, hosts):
    """Resolve a list of {server_id|hostname} dicts into a list of server ids.

    Returns None if hosts is None.
    """
    if hosts is None:
        return None
    return _dedup(
        [
            resolve_host_id(api, host.get("server_id"), host.get("hostname"))
            for host in hosts
        ]
    )


def find_bgp_group(api, bgp_group_id=None, name=None):
    """Find BGP group by id or by name (names are unique).

    Returns group or None if not found.
    """
    if bgp_group_id:
        try:
            return api.get_bgp_group(bgp_group_id)
        except APIError404:
            return None
    if not name:
        raise ModuleError("One of bgp_group_id or name must be provided.")
    found = [
        group
        for group in api.list_bgp_groups(search_pattern=name)
        if group.get("name") == name
    ]
    if len(found) > 1:
        raise ModuleError(f"Multiple BGP groups found with name '{name}'.")
    if found:
        return found[0]
    return None


def _dedup(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _network(value):
    """Parse prefix returned by API (lenient)."""
    try:
        return ipaddress.ip_network(value, strict=False)
    except ValueError:
        return None


def _user_network(value):
    """Parse prefix provided by user (strict)."""
    try:
        return ipaddress.ip_network(value, strict=True)
    except ValueError as e:
        raise ModuleError(
            f"Invalid prefix '{value}': {e}. Expected CIDR notation "
            "(for example, 192.0.2.0/29)."
        )


def _live_prefixes(group):
    """Prefixes which are not being removed, oldest first."""
    prefixes = [
        prefix
        for prefix in group.get("announced_prefixes") or []
        if prefix.get("status") != "removing"
    ]
    return sorted(
        prefixes, key=lambda p: (p.get("created_at") or "", p.get("id") or "")
    )


def plan_prefixes(group, desired, prune):
    """Match desired announced prefixes against existing ones.

    desired is a list of dicts, each with exactly one of:
      - mask: request a prefix with this mask (matched by count);
      - prefix: existing prefix with this CIDR, or, if there is none,
        request to announce this CIDR (API decides if it's permitted);
      - id: existing prefix with this id.

    Prefixes in 'removing' status are ignored.

    Returns dict:
      keep: existing prefixes to keep;
      add: list of dicts to request ({"prefix": cidr} or {"mask": mask});
      remove: existing prefixes to remove (only with prune);
      extra: existing prefixes not matched by desired (only without prune).
    """
    live = _live_prefixes(group)
    pinned_ids = set()
    mask_requests = []
    add = []
    for item in desired:
        if item.get("id"):
            matches = [p for p in live if p.get("id") == item["id"]]
            if not matches:
                raise ModuleError(
                    f"Announced prefix with id {item['id']} is not found in "
                    "the group. Use prefix or mask to request a new prefix."
                )
        elif item.get("prefix"):
            wanted = _user_network(item["prefix"])
            matches = [p for p in live if _network(p.get("prefix") or "") == wanted]
            if not matches:
                request = {"prefix": str(wanted)}
                if request not in add:
                    add.append(request)
                continue
        elif item.get("mask") is not None:
            mask_requests.append(item["mask"])
            continue
        else:
            raise ModuleError(
                "Each item in announced_prefixes needs one of mask, prefix or id."
            )
        pinned_ids.add(matches[0]["id"])

    keep_ids = set(pinned_ids)
    unpinned = [p for p in live if p["id"] not in pinned_ids]
    extra = [p for p in unpinned if p.get("mask") is None]
    masks = sorted(
        set(mask_requests)
        | set(p.get("mask") for p in unpinned if p.get("mask") is not None)
    )
    for mask in masks:
        wanted_count = mask_requests.count(mask)
        candidates = [p for p in unpinned if p.get("mask") == mask]
        if prune and wanted_count and len(candidates) > wanted_count:
            raise ModuleError(
                f"Group has {len(candidates)} unpinned /{mask} prefixes "
                f"({', '.join(p.get('prefix') or p['id'] for p in candidates)}), "
                f"but only {wanted_count} requested. With prune_prefixes it's "
                "ambiguous which ones to remove. Pin prefixes to keep by "
                "prefix or id instead of mask."
            )
        keep_ids.update(p["id"] for p in candidates[:wanted_count])
        missing = max(0, wanted_count - len(candidates))
        add.extend({"mask": mask} for unused in range(missing))
        extra.extend(candidates[wanted_count:])

    if prune:
        remove = extra
        extra = []
    else:
        remove = []
        keep_ids.update(p["id"] for p in extra)
    return {
        "keep": [p for p in live if p["id"] in keep_ids],
        "add": add,
        "remove": remove,
        "extra": extra,
    }


class ScBgpGroupsInfo:
    def __init__(
        self,
        endpoint,
        token,
        search_pattern=None,
        status=None,
        location_id=None,
        location_code=None,
        asn=None,
        server_id=None,
        hostname=None,
        label_selector=None,
    ):
        self.api = ScApi(token, endpoint)
        self.search_pattern = search_pattern
        self.status = status
        self.location_id = location_id
        self.location_code = location_code
        self.asn = asn
        self.server_id = server_id
        self.hostname = hostname
        self.label_selector = label_selector

    def run(self):
        location_id = self.location_id
        if self.location_code:
            location_id = resolve_location_ids(
                self.api, location_codes=[self.location_code]
            )[0]
        server_id = self.server_id
        if self.hostname:
            server_id = resolve_host_id(self.api, hostname=self.hostname)
        groups = self.api.list_bgp_groups(
            search_pattern=self.search_pattern,
            status=self.status,
            location_id=location_id,
            asn=self.asn,
            server_id=server_id,
            label_selector=self.label_selector,
        )
        return {"changed": False, "bgp_groups": list(groups)}


class ScBgpGroupInfo:
    def __init__(self, endpoint, token, bgp_group_id=None, name=None):
        self.api = ScApi(token, endpoint)
        self.bgp_group_id = bgp_group_id
        self.name = name

    def run(self):
        group = find_bgp_group(self.api, self.bgp_group_id, self.name)
        if not group:
            raise ModuleError(
                f"BGP group {self.bgp_group_id or self.name} is not found."
            )
        return {"changed": False, "bgp_group": group}


class ScBgpGroup:
    def __init__(
        self,
        endpoint,
        token,
        state,
        bgp_group_id,
        name,
        network_type,
        asn,
        location_ids,
        location_codes,
        hosts,
        announced_prefixes,
        prune_prefixes,
        labels,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.state = state
        self.bgp_group_id = bgp_group_id
        self.name = name
        self.network_type = network_type
        self.asn = asn
        self.location_ids = location_ids
        self.location_codes = location_codes
        self.hosts = hosts
        self.announced_prefixes = announced_prefixes
        self.prune_prefixes = prune_prefixes
        self.labels = labels
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode
        if wait and update_interval > wait:
            raise ModuleError("update_interval is longer than wait.")

    # Waiting
    def _get(self, group_id, elapsed):
        return self.api.get_bgp_group(
            group_id,
            retry_rules=_retry_rules_for_wait(
                max_wait=max(0, self.wait - elapsed), delay=self.update_interval
            ),
        )

    def wait_for_active(self, group_id, prefixes_settled):
        """Wait until group is active.

        If prefixes_settled is True, also wait until no announced prefix
        is pending.
        """
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            group = self._get(group_id, elapsed)
            status = group.get("status")
            if status == "failed":
                raise ModuleError(f"BGP group {group_id} is in 'failed' status.")
            if status == "removing":
                raise ModuleError(f"BGP group {group_id} is being removed.")
            pending_prefixes = [
                p
                for p in group.get("announced_prefixes") or []
                if p.get("status") == "pending"
            ]
            if status == "active" and not (prefixes_settled and pending_prefixes):
                return group
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for BGP group {group_id} to become "
                    f"active (last status: {status}, pending prefixes: "
                    f"{len(pending_prefixes)}).",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    def wait_for_disappear(self, group_id):
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            try:
                self._get(group_id, elapsed)
            except APIError404:
                return
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for BGP group {group_id} to be deleted.",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    @staticmethod
    def check_new_prefixes(old_group, new_group):
        old_ids = set(p.get("id") for p in old_group.get("announced_prefixes") or [])
        failed = [
            p.get("prefix") or p.get("id")
            for p in new_group.get("announced_prefixes") or []
            if p.get("id") not in old_ids and p.get("status") == "failed"
        ]
        if failed:
            raise ModuleError(
                f"Provisioning of announced prefix(es) failed: {', '.join(failed)}."
            )

    # Present
    def create(self):
        location_ids = resolve_location_ids(
            self.api, self.location_ids, self.location_codes
        )
        host_ids = resolve_host_ids(self.api, self.hosts)
        if not location_ids:
            raise ModuleError(
                "location_ids or location_codes is required to create a BGP group."
            )
        if not host_ids:
            raise ModuleError("hosts is required to create a BGP group.")
        if any(item.get("id") for item in self.announced_prefixes or []):
            raise ModuleError(
                "id can't be used in announced_prefixes for a new group, "
                "it refers to an existing prefix. Use prefix or mask."
            )
        prefixes = plan_prefixes({}, self.announced_prefixes or [], prune=False)[
            "add"
        ]
        network_type = self.network_type or DEFAULT_NETWORK_TYPE
        result = {"changed": True, "prefixes_added": prefixes, "prefixes_removed": []}
        if self.checkmode:
            result["bgp_group"] = {
                "id": None,
                "name": self.name,
                "network_type": network_type,
                "asn": self.asn,
                "session_type": "ebgp" if self.asn is not None else "ibgp",
                "status": "pending",
                "location_ids": location_ids,
                "hosts": [{"server_id": host_id} for host_id in host_ids],
                "announced_prefixes": [dict(p, status="pending") for p in prefixes],
                "labels": self.labels or {},
            }
            return result
        group = self.api.post_bgp_group(
            name=self.name,
            network_type=network_type,
            location_ids=location_ids,
            hosts=[{"server_id": host_id} for host_id in host_ids],
            asn=self.asn,
            announced_prefixes=prefixes,
            labels=self.labels,
        )
        if self.wait:
            group = self.wait_for_active(group["id"], prefixes_settled=True)
            self.check_new_prefixes({}, group)
        result["bgp_group"] = group
        return result

    def check_immutable(self, group):
        if self.network_type and self.network_type != group.get("network_type"):
            raise ModuleError(
                f"network_type of existing BGP group is "
                f"'{group.get('network_type')}', it can't be changed."
            )
        if self.asn is not None:
            if group.get("session_type") == "ibgp":
                raise ModuleError(
                    "Existing BGP group uses iBGP, asn can't be set "
                    "(omit asn for iBGP groups)."
                )
            if group.get("asn") != self.asn:
                raise ModuleError(
                    f"asn of existing BGP group is {group.get('asn')}, "
                    "it can't be changed."
                )

    def compute_update(self, group, location_ids, host_ids):
        """Return (body for PUT, prefix plan or None)."""
        body = {}
        if self.bgp_group_id and self.name and self.name != group.get("name"):
            body["name"] = self.name
        if self.labels is not None and self.labels != (group.get("labels") or {}):
            body["labels"] = self.labels
        if location_ids is not None and set(location_ids) != set(
            group.get("location_ids") or []
        ):
            body["location_ids"] = location_ids
        existing_hosts = set(h.get("server_id") for h in group.get("hosts") or [])
        if host_ids is not None and set(host_ids) != existing_hosts:
            body["hosts"] = [{"server_id": host_id} for host_id in host_ids]
        plan = None
        if self.announced_prefixes is not None:
            plan = plan_prefixes(group, self.announced_prefixes, self.prune_prefixes)
            if plan["add"] or plan["remove"]:
                body["announced_prefixes"] = [
                    {"id": p["id"]} for p in plan["keep"]
                ] + plan["add"]
        return body, plan

    @staticmethod
    def preview(group, body, plan):
        preview = dict(group)
        for key in ("name", "labels", "location_ids", "hosts"):
            if key in body:
                preview[key] = body[key]
        if "announced_prefixes" in body:
            preview["announced_prefixes"] = list(plan["keep"]) + [
                dict(p, status="pending") for p in plan["add"]
            ]
        return preview

    def ensure_active(self, group):
        status = group.get("status")
        if status == "active":
            return group
        if status == "pending":
            if not self.wait:
                raise ModuleError(
                    f"BGP group {group['id']} is pending, it can be updated only "
                    "when active. Use wait to wait for it."
                )
            return self.wait_for_active(group["id"], prefixes_settled=False)
        raise ModuleError(
            f"BGP group {group['id']} is in '{status}' status and can't be updated."
        )

    def update(self, group):
        self.check_immutable(group)
        location_ids = resolve_location_ids(
            self.api, self.location_ids, self.location_codes
        )
        host_ids = resolve_host_ids(self.api, self.hosts)
        body, plan = self.compute_update(group, location_ids, host_ids)
        if body and not self.checkmode and group.get("status") != "active":
            group = self.ensure_active(group)
            self.check_immutable(group)
            body, plan = self.compute_update(group, location_ids, host_ids)
        result = {
            "changed": bool(body),
            "prefixes_added": plan["add"] if plan else [],
            "prefixes_removed": plan["remove"] if plan else [],
        }
        if plan and plan["extra"]:
            result["warnings"] = [
                "BGP group has announced prefixes not listed in announced_prefixes: "
                f"{', '.join(p.get('prefix') or p['id'] for p in plan['extra'])}. "
                "They are kept, use prune_prefixes to remove them."
            ]
        if not body:
            result["bgp_group"] = group
            return result
        if self.checkmode:
            result["bgp_group"] = self.preview(group, body, plan)
            return result
        updated = self.api.put_bgp_group(group["id"], body)
        if self.wait:
            updated = self.wait_for_active(group["id"], prefixes_settled=True)
            self.check_new_prefixes(group, updated)
        result["bgp_group"] = updated
        return result

    # Absent
    def absent(self, group):
        if not group:
            return {"changed": False, "bgp_group": {}}
        group_id = group["id"]
        status = group.get("status")
        if self.checkmode:
            return {"changed": status != "removing", "bgp_group": {}}
        if status == "removing":
            if self.wait:
                self.wait_for_disappear(group_id)
            return {"changed": False, "bgp_group": {}}
        if status == "pending":
            if not self.wait:
                raise ModuleError(
                    f"BGP group {group_id} is pending, it can be deleted only "
                    "when active. Use wait to wait for it."
                )
            self.wait_for_active(group_id, prefixes_settled=False)
        self.api.delete_bgp_group(group_id)
        if self.wait:
            self.wait_for_disappear(group_id)
        return {"changed": True, "bgp_group": {}}

    def run(self):
        group = find_bgp_group(self.api, self.bgp_group_id, self.name)
        if self.state == "absent":
            return self.absent(group)
        if not group:
            if self.bgp_group_id:
                raise ModuleError(f"BGP group {self.bgp_group_id} is not found.")
            return self.create()
        return self.update(group)
