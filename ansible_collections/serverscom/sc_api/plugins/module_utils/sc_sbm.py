from __future__ import absolute_import, division, print_function
import re
import time

from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    APIError404,
    APIError409,
    ScApi,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
    CHANGED,
    NOT_CHANGED,
    _retry_rules_for_wait,
)


__metaclass__ = type


class ScSbmServerInfo:
    """Get single SBM server info with ready state check."""

    def __init__(self, endpoint, token, server_id, fail_on_absent):
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.fail_on_absent = fail_on_absent

    @staticmethod
    def _is_server_ready(server_info):
        if (
            server_info.get("status") == "active"
            and server_info.get("power_status") == "powered_on"
            and server_info.get("operational_status") == "normal"
        ):
            return True
        return False

    def run(self):
        try:
            server_info = self.api.get_sbm_servers(self.server_id)
        except APIError404 as e:
            if self.fail_on_absent:
                raise e
            return {"changed": False, "found": False, "ready": False}
        module_output = server_info
        module_output["found"] = True
        module_output["ready"] = self._is_server_ready(server_info)
        module_output["changed"] = False
        return module_output


class ScSbmServerPower:
    """Power on/off/cycle with wait support."""

    def __init__(self, endpoint, token, server_id, state, wait, checkmode):
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.state = state
        self.wait = wait
        self.checkmode = checkmode
        self.interval = 5

    def wait_for_status(self, target_status):
        start = time.time()
        while True:
            elapsed = time.time() - start
            server = self.api.get_sbm_servers(
                self.server_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.interval,
                ),
            )
            status = server["power_status"]
            if status == target_status:
                return server
            if status not in ("powering_on", "powering_off", "power_cycling"):
                raise ModuleError(
                    f"Unexpected power_status={status}, expected {target_status}"
                )
            if elapsed > self.wait:
                raise ModuleError(
                    f"Timeout waiting for power_status={target_status}, last={status}"
                )
            time.sleep(self.interval)

    def _retry_on_conflict(self, action):
        """Call action(), retrying on 409 CONFLICT until wait timeout.

        Only retries when the API error code is ``CONFLICT``
        (power management temporarily unavailable).  Other 409 errors
        (e.g. ``NETWORK_IS_NOT_READY``) are not retried.
        """
        start = time.time()
        while True:
            try:
                action()
                return
            except APIError409 as e:
                if '"code":"CONFLICT"' not in e.msg:
                    raise
                if time.time() - start > self.wait:
                    raise
                time.sleep(self.interval)

    def power_on(self):
        try:
            server = self.api.get_sbm_servers(self.server_id)
        except APIError404:
            raise ModuleError(f"Server {self.server_id} not found.")
        if server["power_status"] == "powered_on":
            server["changed"] = False
            return server
        if self.checkmode:
            server["changed"] = True
            return server
        self._retry_on_conflict(
            lambda: self.api.post_sbm_server_power_on(self.server_id)
        )
        server = self.wait_for_status("powered_on")
        server["changed"] = True
        return server

    def power_off(self):
        try:
            server = self.api.get_sbm_servers(self.server_id)
        except APIError404:
            raise ModuleError(f"Server {self.server_id} not found.")
        if server["power_status"] == "powered_off":
            server["changed"] = False
            return server
        if self.checkmode:
            server["changed"] = True
            return server
        self._retry_on_conflict(
            lambda: self.api.post_sbm_server_power_off(self.server_id)
        )
        server = self.wait_for_status("powered_off")
        server["changed"] = True
        return server

    def power_cycle(self):
        try:
            server = self.api.get_sbm_servers(self.server_id)
        except APIError404:
            raise ModuleError(f"Server {self.server_id} not found.")
        if self.checkmode:
            server["changed"] = True
            return server
        self._retry_on_conflict(
            lambda: self.api.post_sbm_server_power_cycle(self.server_id)
        )
        server = self.wait_for_status("powered_on")
        server["changed"] = True
        return server

    def run(self):
        if self.state == "on":
            return self.power_on()
        elif self.state == "off":
            return self.power_off()
        elif self.state == "cycle":
            return self.power_cycle()
        else:
            raise ModuleError(f"Unknown state: {self.state}")


class ScSbmServerReinstall:
    """Reinstall OS on SBM server.

    Key difference from dedicated: NO drives_layout parameter (SBM API doesn't support it).
    Uses sbm_flavor_model_id instead of server_model_id for OS lookup.
    """

    def __init__(
        self,
        endpoint,
        token,
        server_id,
        hostname,
        operating_system_id,
        operating_system_regex,
        ssh_keys,
        ssh_key_name,
        user_data,
        wait,
        update_interval,
        checkmode,
    ):
        if wait:
            if int(wait) < int(update_interval):
                raise ModuleError(
                    f"Update interval ({update_interval}) is longer "
                    f"than wait time ({wait})"
                )
        self.api = ScApi(token, endpoint)
        self.server_data = None
        self.server_id = server_id
        self.hostname = self.get_hostname(hostname)
        self.operating_system_regex = operating_system_regex
        self.operating_system_id = self.get_operating_system_id(
            operating_system_id, operating_system_regex
        )
        self.ssh_keys = self.get_ssh_keys(ssh_keys, ssh_key_name)
        self.wait = wait
        self.update_interval = update_interval
        self.user_data = user_data
        self.checkmode = checkmode

    def get_server_data(self):
        if not self.server_data:
            self.server_data = self.api.get_sbm_servers(self.server_id)

    def get_hostname(self, hostname):
        if hostname:
            return hostname
        self.get_server_data()
        if "title" not in self.server_data:
            raise ModuleError(
                "Unable to retrieve old title for the server. "
                "Use hostname option to specify the hostname for reinstall."
            )
        return self.server_data["title"]

    def get_os_id_by_regex(self):
        self.get_server_data()

        cfg = self.server_data.get("configuration_details") or {}
        sbm_flavor_model_id = cfg.get("sbm_flavor_model_id")
        sbm_flavor_model_name = cfg.get("sbm_flavor_model_name")
        server_location_id = self.server_data.get("location_id")
        server_location_code = self.server_data.get("location_code")

        if not sbm_flavor_model_id:
            raise ModuleError(
                "Can't obtain sbm_flavor_model_id which is required to get OS ID"
            )
        if not server_location_id:
            raise ModuleError(
                "Can't obtain server_location_id which is required to get OS ID"
            )

        os_list = list(
            self.api.list_os_images_by_sbm_flavor_id(
                server_location_id, sbm_flavor_model_id
            )
        )
        if not os_list:
            raise ModuleError(
                f"No available OS options found for SBM flavor model '{sbm_flavor_model_name}' "
                f"in location '{server_location_code}'"
            )

        try:
            pattern = re.compile(self.operating_system_regex, flags=re.IGNORECASE)
        except re.error as e:
            raise ModuleError(f"Invalid operating_system_regex: {e}")

        filtered = [os for os in os_list if pattern.search(os.get("full_name", ""))]
        if len(filtered) == 1:
            return int(filtered[0]["id"])
        if len(filtered) > 1:
            names = ", ".join(
                os.get("full_name") or str(os.get("id")) for os in filtered
            )
            raise ModuleError(
                f"Multiple OS options match the regex '{self.operating_system_regex}': {names}"
            )
        raise ModuleError(
            f"No OS options match the regex '{self.operating_system_regex}' for "
            f"SBM flavor model '{sbm_flavor_model_name}' in location '{server_location_code}'"
        )

    def get_operating_system_id(self, operating_system_id, operating_system_regex):
        if operating_system_id is not None:
            return int(operating_system_id)

        self.get_server_data()
        if operating_system_regex:
            return self.get_os_id_by_regex()

        cfg = self.server_data.get("configuration_details") or {}
        if "operating_system_id" not in cfg:
            raise ModuleError(
                "No operating_system_id was given, and unable to get old operating_system_id"
            )
        return int(cfg["operating_system_id"])

    def get_ssh_keys(self, ssh_keys, ssh_key_name):
        if ssh_keys:
            return ssh_keys
        if not ssh_key_name:
            return []
        return [
            self.api.toolbox.get_ssh_fingerprints_by_key_name(ssh_key_name, must=True)
        ]

    def wait_for_server(self):
        ready = False
        start_time = time.time()
        elapsed = 0
        while not ready:
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(msg="Server is not ready.", timeout=elapsed)
            server_info = self.api.get_sbm_servers(
                self.server_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
            ready = ScSbmServerInfo._is_server_ready(server_info)
        server_info["ready"] = True
        server_info["elapsed"] = elapsed
        return server_info

    def run(self):
        if self.checkmode:
            return {"changed": True}
        result = self.api.post_sbm_server_reinstall(
            server_id=self.server_id,
            hostname=self.hostname,
            operating_system_id=self.operating_system_id,
            ssh_key_fingerprints=self.ssh_keys,
            user_data=self.user_data,
        )
        if self.wait:
            result = self.wait_for_server()
        result["changed"] = True
        return result


class ScSbmServerPtr:
    """Manage PTR records for SBM server."""

    def __init__(
        self,
        endpoint,
        token,
        state,
        server_id,
        ip,
        domain,
        ttl,
        priority,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.state = state
        self.server_id = server_id
        self.ip = ip
        self.domain = domain
        self.ttl = ttl
        self.priority = priority
        self.checkmode = checkmode

    def find_ptr(self, ptr_records, domain, ip):
        for record in ptr_records:
            if domain and domain != record["domain"]:
                continue
            if ip and ip != record["ip"]:
                continue
            if domain or ip:
                yield record

    def run(self):
        ptr_records = list(self.api.list_sbm_server_ptr_records(self.server_id))
        if self.state == "query":
            return {"changed": False, "ptr_records": ptr_records}
        elif self.state == "present":
            if list(self.find_ptr(ptr_records, self.domain, self.ip)):
                return {"changed": False, "ptr_records": ptr_records}
            if self.checkmode:
                return {"changed": True, "ptr_records": ptr_records}
            self.api.post_sbm_server_ptr_record(
                server_id=self.server_id,
                ip=self.ip,
                domain=self.domain,
                ttl=self.ttl,
                priority=self.priority,
            )
            return {
                "changed": True,
                "ptr_records": list(
                    self.api.list_sbm_server_ptr_records(self.server_id)
                ),
            }
        elif self.state == "absent":
            if not list(self.find_ptr(ptr_records, self.domain, self.ip)):
                return {"changed": False, "ptr_records": ptr_records}
            if self.checkmode:
                return {"changed": True, "ptr_records": ptr_records}
            for record in self.find_ptr(ptr_records, self.domain, self.ip):
                self.api.delete_sbm_server_ptr_record(
                    server_id=self.server_id, record_id=record["id"]
                )
            return {
                "changed": True,
                "ptr_records": list(
                    self.api.list_sbm_server_ptr_records(self.server_id)
                ),
            }
        else:
            raise ModuleError(f"Unknown state={self.state}")


class ScSbmFlavorModelsInfo:
    """List SBM flavor models for a location."""

    def __init__(self, endpoint, token, location_id, search_pattern):
        self.api = ScApi(token, endpoint)
        self.location_id = location_id
        self.search_pattern = search_pattern

    def run(self):
        return {
            "changed": False,
            "sbm_flavor_models": list(
                self.api.list_sbm_flavor_models(self.location_id, self.search_pattern)
            ),
        }


class ScSbmServerCreate:
    """Create (order) an SBM server."""

    def __init__(
        self,
        endpoint,
        token,
        location_id,
        sbm_flavor_model_id,
        hostname,
        operating_system_id,
        ssh_key_fingerprints,
        user_data,
        wait,
        update_interval,
        checkmode,
    ):
        if wait and int(update_interval) > int(wait):
            raise ModuleError(
                f"Update interval ({update_interval}) is longer than wait time ({wait})"
            )
        self.api = ScApi(token, endpoint)
        self.location_id = location_id
        self.sbm_flavor_model_id = sbm_flavor_model_id
        self.hostname = hostname
        self.operating_system_id = operating_system_id
        self.ssh_key_fingerprints = ssh_key_fingerprints
        self.user_data = user_data
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def wait_for_server(self, server):
        start_time = time.time()
        while not ScSbmServerInfo._is_server_ready(server):
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for SBM server {server.get('id')} "
                    f"to become ready. Last status: "
                    f"status={server.get('status')}, "
                    f"power_status={server.get('power_status')}, "
                    f"operational_status={server.get('operational_status')}",
                    timeout=elapsed,
                )
            server = self.api.get_sbm_servers(
                server["id"],
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
        return server

    def run(self):
        if self.checkmode:
            return {
                "changed": True,
                "info": "Server should be created, "
                "but check_mode is activated. "
                "No real server was created.",
            }
        result = self.api.post_sbm_servers(
            location_id=self.location_id,
            sbm_flavor_model_id=self.sbm_flavor_model_id,
            hosts=[{"hostname": self.hostname}],
            operating_system_id=self.operating_system_id,
            ssh_key_fingerprints=self.ssh_key_fingerprints,
            user_data=self.user_data,
        )
        server = result[0]
        if self.wait:
            server = self.wait_for_server(server)
        server["changed"] = True
        return server


class ScSbmServerDelete:
    """Delete (release) an SBM server.

    SBM server deletion is not instant — the server is released at the
    end of the current billing hour.  By default the module only sends
    the delete request and returns immediately.  Set *wait_for_deletion*
    to True (and a non-zero *wait*) to poll until the server disappears.
    """

    def __init__(
        self,
        endpoint,
        token,
        server_id,
        wait,
        update_interval,
        retry_on_conflicts,
        wait_for_deletion,
        checkmode,
    ):
        if wait and int(update_interval) > int(wait):
            raise ModuleError(
                f"Update interval ({update_interval}) is longer than wait time ({wait})"
            )
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.wait = wait
        self.update_interval = update_interval
        self.retry_on_conflicts = retry_on_conflicts
        self.wait_for_deletion = wait_for_deletion
        self.checkmode = checkmode

    def retry_to_delete(self):
        start_time = time.time()
        while True:
            try:
                self.api.delete_sbm_server(self.server_id)
                return
            except APIError409:
                if self.retry_on_conflicts:
                    elapsed = time.time() - start_time
                    if elapsed > self.wait:
                        raise WaitError(
                            msg=f"Timeout retrying delete for "
                            f"SBM server {self.server_id}",
                            timeout=elapsed,
                        )
                    time.sleep(self.update_interval)
                else:
                    raise
            except APIError404:
                return

    def wait_for_disappearance(self):
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            try:
                self.api.get_sbm_servers(
                    self.server_id,
                    retry_rules=_retry_rules_for_wait(
                        max_wait=max(0, self.wait - elapsed),
                        delay=self.update_interval,
                    ),
                )
            except APIError404:
                return
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for SBM server {self.server_id} to disappear",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    def run(self):
        try:
            server = self.api.get_sbm_servers(self.server_id)
        except APIError404:
            return {"changed": False}
        if self.checkmode:
            server["changed"] = True
            return server
        self.retry_to_delete()
        if self.wait_for_deletion and self.wait:
            self.wait_for_disappearance()
        server["changed"] = True
        return server


class ScSbmServersInfo:
    """List all SBM servers."""

    def __init__(
        self,
        endpoint,
        token,
        search_pattern=None,
        location_id=None,
        rack_id=None,
        label_selector=None,
    ):
        self.api = ScApi(token, endpoint)
        self.search_pattern = search_pattern
        self.location_id = location_id
        self.rack_id = rack_id
        self.label_selector = label_selector

    def run(self):
        return {
            "changed": False,
            "sbm_servers": list(
                self.api.list_sbm_servers(
                    search_pattern=self.search_pattern,
                    location_id=self.location_id,
                    rack_id=self.rack_id,
                    label_selector=self.label_selector,
                )
            ),
        }


class ScSbmServerLabels:
    """Update labels on an SBM server."""

    def __init__(self, endpoint, token, server_id, labels, checkmode):
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.labels = labels
        self.checkmode = checkmode

    def run(self):
        try:
            server = self.api.get_sbm_servers(self.server_id)
        except APIError404:
            raise ModuleError(f"Server {self.server_id} not found.")
        if server.get("labels") == self.labels:
            server["changed"] = NOT_CHANGED
            return server
        if self.checkmode:
            server["changed"] = CHANGED
            return server
        _status_code, server = self.api.put_sbm_server(self.server_id, self.labels)
        server["changed"] = CHANGED
        return server


class ScSbmServerNetworksInfo:
    """List or get networks for an SBM server."""

    def __init__(
        self,
        endpoint,
        token,
        server_id,
        network_id=None,
        search_pattern=None,
        family=None,
        interface_type=None,
        distribution_method=None,
        additional=None,
    ):
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.network_id = network_id
        self.search_pattern = search_pattern
        self.family = family
        self.interface_type = interface_type
        self.distribution_method = distribution_method
        self.additional = additional

    def run(self):
        if self.network_id:
            network = self.api.get_sbm_server_network(self.server_id, self.network_id)
            network["changed"] = NOT_CHANGED
            return network
        return {
            "changed": False,
            "networks": list(
                self.api.list_sbm_server_networks(
                    server_id=self.server_id,
                    search_pattern=self.search_pattern,
                    family=self.family,
                    interface_type=self.interface_type,
                    distribution_method=self.distribution_method,
                    additional=self.additional,
                )
            ),
        }


class ScSbmServerNetwork:
    """Create or delete a network for an SBM server."""

    def __init__(
        self,
        endpoint,
        token,
        server_id,
        state,
        network_id=None,
        mask=None,
        distribution_method=None,
        wait=600,
        update_interval=10,
        checkmode=False,
    ):
        if wait and int(update_interval) > int(wait):
            raise ModuleError(
                f"Update interval ({update_interval}) is longer than wait time ({wait})"
            )
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.state = state
        self.network_id = network_id
        self.mask = mask
        self.distribution_method = distribution_method
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def run(self):
        if self.state == "present":
            return self.create()
        elif self.state == "absent":
            return self.delete()
        else:
            raise ModuleError(f"Unknown state={self.state}")

    @staticmethod
    def _is_network_active(network):
        return network.get("status") == "active"

    def _wait_for_network_active(self, network):
        start_time = time.time()
        while not self._is_network_active(network):
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for network {network.get('id')} "
                    f"to become active. Last status: {network.get('status')}",
                    timeout=elapsed,
                )
            network = self.api.get_sbm_server_network(
                self.server_id,
                network["id"],
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
        return network

    def create(self):
        if self.checkmode:
            return {"changed": CHANGED}
        network = self.api.post_sbm_server_private_ipv4_network(
            server_id=self.server_id,
            mask=self.mask,
            distribution_method=self.distribution_method,
        )
        if self.wait:
            network = self._wait_for_network_active(network)
        network["changed"] = CHANGED
        return network

    def _wait_for_network_gone(self):
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            try:
                network = self.api.get_sbm_server_network(
                    self.server_id,
                    self.network_id,
                    retry_rules=_retry_rules_for_wait(
                        max_wait=max(0, self.wait - elapsed),
                        delay=self.update_interval,
                    ),
                )
            except APIError404:
                return
            if network.get("status") == "removed":
                return
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for network {self.network_id} "
                    f"to be removed. Last status: {network.get('status')}",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    def delete(self):
        try:
            network = self.api.get_sbm_server_network(self.server_id, self.network_id)
        except APIError404:
            return {"changed": NOT_CHANGED}
        if network.get("status") == "removed":
            return {"changed": NOT_CHANGED}
        if self.checkmode:
            return {"changed": CHANGED}
        start_time = time.time()
        while True:
            try:
                self.api.delete_sbm_server_network(self.server_id, self.network_id)
                break
            except APIError409:
                elapsed = time.time() - start_time
                if not self.wait or elapsed > self.wait:
                    raise
                time.sleep(self.update_interval)
        if self.wait:
            self._wait_for_network_gone()
        return {"changed": CHANGED}


class ScSbmOSList:
    """List available OS images for an SBM flavor model."""

    def __init__(
        self,
        endpoint,
        token,
        location_id,
        sbm_flavor_model_id=None,
        sbm_flavor_model_name=None,
        os_name_regex=None,
    ):
        self.api = ScApi(token, endpoint)
        self.location_id = location_id
        self.sbm_flavor_model_id = sbm_flavor_model_id
        self.sbm_flavor_model_name = sbm_flavor_model_name
        self.os_name_regex = os_name_regex

    def get_os_list_by_sbm_flavor_model_name(self):
        if not self.sbm_flavor_model_name:
            raise ModuleError(
                "sbm_flavor_model_name is required to get OS list by SBM flavor model name"
            )
        flavors = self.api.list_sbm_flavor_models(
            self.location_id, search_pattern=self.sbm_flavor_model_name
        )
        for flavor in flavors:
            if flavor.get("name") == self.sbm_flavor_model_name:
                return list(
                    self.api.list_os_images_by_sbm_flavor_id(
                        self.location_id, flavor.get("id")
                    )
                )
        raise ModuleError(f"SBM flavor model {self.sbm_flavor_model_name} not found")

    def apply_os_name_filter(self, os_list):
        if self.os_name_regex:
            pattern = re.compile(self.os_name_regex)
            return [os for os in os_list if pattern.search(os.get("full_name", ""))]
        return os_list

    def run(self):
        if self.sbm_flavor_model_name:
            os_list = self.get_os_list_by_sbm_flavor_model_name()
        elif self.sbm_flavor_model_id:
            os_list = list(
                self.api.list_os_images_by_sbm_flavor_id(
                    self.location_id, self.sbm_flavor_model_id
                )
            )
        else:
            raise ModuleError(
                "One of sbm_flavor_model_name or sbm_flavor_model_id must be provided"
            )
        os_list = self.apply_os_name_filter(os_list)

        return {"changed": False, "os_list": os_list}
