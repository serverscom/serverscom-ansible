from __future__ import absolute_import, division, print_function
import re
import time

from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    APIError404,
    APIError409,
    APIError412,
    ScApi,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
    _retry_rules_for_wait,
)


__metaclass__ = type


class ScDedicatedServerInfo(object):
    def __init__(self, endpoint, token, name, fail_on_absent):
        self.api = ScApi(token, endpoint)
        self.server_id = name
        self.fail_on_absent = fail_on_absent

    @staticmethod
    def _is_server_ready(server_info):
        if (
            server_info.get("status") == "active"
            and server_info.get("power_status") == "powered_on"
            and server_info.get("operational_status") == "normal"
        ):
            return True
        else:
            return False

    def run(self):
        try:
            server_info = self.api.get_dedicated_servers(self.server_id)
        except APIError404 as e:
            if self.fail_on_absent:
                raise e
            return {"changed": False, "found": False, "ready": False}
        module_output = server_info
        module_output["found"] = True
        module_output["ready"] = self._is_server_ready(server_info)
        module_output["changed"] = False
        return module_output


class ScBaremetalServersInfo:
    def __init__(self, search_pattern, label_selector, type, endpoint, token):
        self.type = type
        self.search_pattern = search_pattern
        self.label_selector = label_selector
        self.api = ScApi(token, endpoint)

    def run(self):
        return {
            "changed": False,
            "baremetal_servers": list(
                self.api.list_hosts(self.type, self.search_pattern, self.label_selector)
            ),
        }


class ScBaremetalLocationsInfo(object):
    def __init__(self, endpoint, token, search_pattern, required_features):
        self.search_pattern = search_pattern
        self.required_features = required_features
        self.api = ScApi(token, endpoint)

    @staticmethod
    def location_features(location):
        features = set(location["supported_features"])
        for key, value in location.items():
            # fiter out both non-feature things like name, and
            # disabled features,
            if value is True:
                features.add(key)
        return features

    def locations(self):
        all_locations = list(self.api.list_locations(self.search_pattern))
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

    def run(self):
        ret_data = {"changed": False}
        ret_data["locations"] = self.locations()
        return ret_data


class ScDedicatedServerReinstall(object):
    def __init__(
        self,
        endpoint,
        token,
        server_id,
        hostname,
        drives_layout_template,
        drives_layout,
        operating_system_id,
        operating_system_regex,
        ssh_keys,
        ssh_key_name,
        wait,
        update_interval,
        user_data,
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
        self.drives_layout = self.get_drives_layout(
            drives_layout, drives_layout_template
        )
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
            self.server_data = self.api.get_dedicated_servers(self.server_id)

    def get_hostname(self, hostname):
        if hostname:
            return hostname
        self.get_server_data()
        if "title" not in self.server_data:
            raise ModuleError(
                "Unable to retrieve old title for the server. "
                "use hostname option to specify the hostname for reinstall."
            )
        return self.server_data["title"]

    def get_os_id_by_regex(self):
        self.get_server_data()  # ensure populated

        cfg = self.server_data.get("configuration_details") or {}
        server_model_id = cfg.get("server_model_id")
        server_model_name = cfg.get("server_model_name")
        server_location_id = self.server_data.get("location_id")
        server_location_code = self.server_data.get("location_code")

        if not server_model_id:
            raise ModuleError(
                "Can't obtain server_model_id which is required to get OS ID"
            )
        if not server_location_id:
            raise ModuleError(
                "Can't obtain server_location_id which is required to get OS ID"
            )

        os_list = list(
            self.api.list_os_images_by_model_id(server_location_id, server_model_id)
        )
        if not os_list:
            raise ModuleError(
                f"No available OS options found for server model '{server_model_name}' "
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
            f"server model '{server_model_name}' in location '{server_location_code}'"
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

    @staticmethod
    def get_drives_layout(layout, template):
        partitions_template = [
            {"target": "/boot", "size": 1024, "fill": False, "fs": "ext4"},
            {"target": "swap", "size": 4096, "fill": False},
            {"target": "/", "fill": True, "fs": "ext4"},
        ]
        rai1_simple = [
            {"slot_positions": [0, 1], "raid": 1, "partitions": partitions_template}
        ]
        raid0_simple = [
            {"slot_positions": [0, 1], "raid": 0, "partitions": partitions_template}
        ]
        no_raid = [{"slot_positions": [0], "partitions": partitions_template}]
        templates = {
            "raid1-simple": rai1_simple,
            "raid0-simple": raid0_simple,
            "no-raid": no_raid,
        }
        if layout:
            return layout
        if template not in templates:
            raise ModuleError("Invalid drives_layout_template.")
        else:
            return templates[template]

    def wait_for_server(self):
        ready = False
        start_time = time.time()
        elapsed = 0
        while not ready:
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(msg="Server is not ready.", timeout=elapsed)
            server_info = self.api.get_dedicated_servers(
                self.server_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
            ready = ScDedicatedServerInfo._is_server_ready(server_info)
        server_info["ready"] = True
        server_info["elapsed"] = elapsed
        return server_info

    def run(self):
        if self.checkmode:
            return {"changed": True}
        result = self.api.post_dedicated_server_reinstall(
            server_id=self.server_id,
            hostname=self.hostname,
            operating_system_id=self.operating_system_id,
            ssh_key_fingerprints=self.ssh_keys,
            user_data=self.user_data,
            drives={
                "layout": self.drives_layout,
            },
        )
        if self.wait:
            result = self.wait_for_server()
        result["changed"] = True
        return result


class ScDedicatedServerPower:
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
            server = self.api.get_dedicated_servers(
                self.server_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.interval,
                ),
            )
            status = server["power_status"]
            if status == target_status:
                return server
            # only these are transitional
            if status not in ("powering_on", "powering_off", "power_cycling"):
                raise ModuleError(
                    f"Unexpected power_status={status}, expected {target_status}"
                )
            if elapsed > self.wait:
                raise ModuleError(
                    f"Timeout waiting for power_status={target_status}, last={status}"
                )
            time.sleep(self.interval)

    def power_on(self):
        try:
            server = self.api.get_dedicated_servers(self.server_id)
        except APIError404:
            raise ModuleError(f"Server {self.server_id} not found.")
        if server["power_status"] == "powered_on":
            server["changed"] = False
            return server
        if self.checkmode:
            server["changed"] = True
            return server
        self.api.post_dedicated_server_power_on(self.server_id)
        server = self.wait_for_status("powered_on")
        server["changed"] = True
        return server

    def power_off(self):
        try:
            server = self.api.get_dedicated_servers(self.server_id)
        except APIError404:
            raise ModuleError(f"Server {self.server_id} not found.")
        if server["power_status"] == "powered_off":
            server["changed"] = False
            return server
        if self.checkmode:
            server["changed"] = True
            return server
        self.api.post_dedicated_server_power_off(self.server_id)
        server = self.wait_for_status("powered_off")
        server["changed"] = True
        return server

    def power_cycle(self):
        try:
            server = self.api.get_dedicated_servers(self.server_id)
        except APIError404:
            raise ModuleError(f"Server {self.server_id} not found.")
        if self.checkmode:
            server["changed"] = True
            return server
        self.api.post_dedicated_server_power_off(self.server_id)
        self.wait_for_status("powered_off")
        self.api.post_dedicated_server_power_on(self.server_id)
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


class ScDedicatedServerIpxe:
    TRANSITIONAL_STATUSES = ("activation", "deactivation")

    def __init__(
        self,
        endpoint,
        token,
        server_id,
        state,
        ipxe_config,
        wait,
        update_interval,
        checkmode,
    ):
        if wait and int(wait) < int(update_interval):
            raise ModuleError(
                f"Update interval ({update_interval}) is longer "
                f"than wait time ({wait})"
            )
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.state = state
        if state in ("public", "private"):
            self.feature_name = f"{state}_ipxe_boot"
            opposite = "private" if state == "public" else "public"
            self.opposite_feature_name = f"{opposite}_ipxe_boot"
        self.ipxe_config = ipxe_config
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def _get_feature_by_name(self, feature_name, retry_rules=None):
        features = self.api.get_dedicated_server_features(
            self.server_id, retry_rules=retry_rules
        )
        for feature in features:
            if feature.get("name") == feature_name:
                return feature
        return None

    def _get_feature_status(self, retry_rules=None):
        feature = self._get_feature_by_name(
            self.feature_name, retry_rules=retry_rules
        )
        if feature is None:
            raise ModuleError(
                f"Feature '{self.feature_name}' not found "
                f"for server {self.server_id}"
            )
        return feature

    def _get_opposite_feature_status(self):
        return self._get_feature_by_name(self.opposite_feature_name)

    def wait_for_status(self, target_status, feature_name=None):
        if feature_name is None:
            feature_name = self.feature_name
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for {feature_name} "
                    f"to reach '{target_status}'",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)
            elapsed = time.time() - start
            feature = self._get_feature_by_name(
                feature_name,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
            if feature is None:
                raise ModuleError(
                    f"Feature '{feature_name}' not found "
                    f"for server {self.server_id}"
                )
            status = feature.get("status")
            if status == target_status:
                return feature
            if status not in self.TRANSITIONAL_STATUSES:
                raise ModuleError(
                    f"Unexpected status '{status}' for {feature_name}, "
                    f"expected '{target_status}'"
                )

    def _deactivate_feature(self, feature_name, status):
        """Deactivate a feature handling all possible statuses.

        Returns (changed, feature) where changed indicates whether
        a deactivation was initiated by us.
        """
        if status in ("deactivated", "incompatible", "unavailable"):
            return False, None
        if status == "activated":
            self.api.post_dedicated_server_feature_deactivate(
                self.server_id, feature_name
            )
            feature = None
            if self.wait:
                feature = self.wait_for_status(
                    "deactivated", feature_name=feature_name
                )
            return True, feature
        if status == "activation":
            if self.wait:
                self.wait_for_status(
                    "activated", feature_name=feature_name
                )
            self.api.post_dedicated_server_feature_deactivate(
                self.server_id, feature_name
            )
            feature = None
            if self.wait:
                feature = self.wait_for_status(
                    "deactivated", feature_name=feature_name
                )
            return True, feature
        if status == "deactivation":
            feature = None
            if self.wait:
                feature = self.wait_for_status(
                    "deactivated", feature_name=feature_name
                )
            return False, feature
        raise ModuleError(
            f"Unexpected status '{status}' for {feature_name}"
        )

    def _deactivate_opposite(self, opposite):
        self._deactivate_feature(
            self.opposite_feature_name, opposite.get("status")
        )

    def _opposite_needs_deactivation(self, opposite):
        if opposite is None:
            return False
        return opposite.get("status") in (
            "activated", "activation", "deactivation"
        )

    def _ensure_present(self):
        feature = self._get_feature_status()
        status = feature.get("status")

        if status == "activated":
            if self.ipxe_config is not None:
                server = self.api.get_dedicated_servers(self.server_id)
                current_config = server.get("ipxe_config") or ""
                if current_config == self.ipxe_config:
                    return {"changed": False, "feature": feature}
                if self.checkmode:
                    return {"changed": True, "feature": feature}
                self.api.put_dedicated_server(
                    self.server_id, {"ipxe_config": self.ipxe_config}
                )
                return {"changed": True, "feature": feature}
            return {"changed": False, "feature": feature}

        if status in ("deactivated", "incompatible", "unavailable"):
            opposite = self._get_opposite_feature_status()
            if self._opposite_needs_deactivation(opposite):
                if self.checkmode:
                    return {"changed": True, "feature": feature}
                self._deactivate_opposite(opposite)
            if self.checkmode:
                return {"changed": True, "feature": feature}
            body = {}
            if self.ipxe_config is not None:
                body["ipxe_config"] = self.ipxe_config
            self.api.post_dedicated_server_feature_activate(
                self.server_id, self.feature_name, body=body or None
            )
            if self.wait:
                feature = self.wait_for_status("activated")
            return {"changed": True, "feature": feature}

        if status == "activation":
            if self.wait:
                feature = self.wait_for_status("activated")
            return {"changed": False, "feature": feature}

        raise ModuleError(
            f"Unexpected status '{status}' for {self.feature_name}"
        )

    def _ensure_absent(self):
        features = self.api.get_dedicated_server_features(self.server_id)
        for feature_name in ("public_ipxe_boot", "private_ipxe_boot"):
            feature = None
            for f in features:
                if f.get("name") == feature_name:
                    feature = f
                    break
            if feature is None:
                continue

            status = feature.get("status")

            if status in ("deactivated", "incompatible", "unavailable"):
                continue

            if self.checkmode:
                return {"changed": True, "feature": feature}

            changed, result_feature = self._deactivate_feature(
                feature_name, status
            )
            return {
                "changed": changed,
                "feature": result_feature or feature,
            }

        # Both features are inactive or absent
        for f in features:
            if f.get("name") in ("public_ipxe_boot", "private_ipxe_boot"):
                return {"changed": False, "feature": f}
        return {"changed": False, "feature": {}}

    def run(self):
        if self.state in ("public", "private"):
            return self._ensure_present()
        else:
            return self._ensure_absent()


class ScDedicatedOSList:
    def __init__(
        self,
        endpoint,
        token,
        server_id,
        location_id,
        location_code,
        server_model_id,
        server_model_name,
        os_name_regex,
    ):
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.location_id = location_id
        self.location_code = location_code
        self.server_model_id = server_model_id
        self.server_model_name = server_model_name
        self.os_name_regex = os_name_regex

        if self.server_id:
            try:
                server = self.api.get_dedicated_servers(self.server_id)
            except APIError404:
                raise ModuleError(f"Server with id '{self.server_id}' not found.")
            self.server_model_id = server["configuration_details"]["server_model_id"]
            self.location_id = server.get("location_id")

        if not self.location_id and self.location_code:
            self.location_code = self.location_code.upper()
            locations = self.api.list_locations(search_pattern=self.location_code)

            for location in locations:
                if location.get("code") == self.location_code:
                    self.location_id = location.get("id")
                    break

            if not self.location_id:
                raise ModuleError(
                    f"Location with code '{self.location_code}' not found."
                )

    def get_os_list_by_model_name(self):
        if not self.server_model_name:
            raise ModuleError(
                "server_model_name is required to get OS list by model name"
            )
        models = self.api.list_server_models(
            self.location_id, search_pattern=self.server_model_name
        )
        for model in models:
            if model.get("name") == self.server_model_name:
                return list(
                    self.api.list_os_images_by_model_id(
                        self.location_id, model.get("id")
                    )
                )
        raise ModuleError(f"Server model {self.server_model_name} not found")

    def apply_os_name_filter(self, os_list):
        if self.os_name_regex:
            pattern = re.compile(self.os_name_regex)
            return [os for os in os_list if pattern.search(os.get("full_name", ""))]
        return os_list

    def run(self):
        if self.server_model_name:
            os_list = self.get_os_list_by_model_name()
        elif self.server_model_id:
            os_list = list(
                self.api.list_os_images_by_model_id(
                    self.location_id, self.server_model_id
                )
            )
        else:
            raise ModuleError(
                "One of server_model_name or server_model_id must be provided"
            )
        os_list = self.apply_os_name_filter(os_list)
        if not os_list:
            raise ModuleError("No operating systems found matching the criteria")

        return {"changed": False, "os_list": os_list}


class ScDedicatedServerRescue:
    def __init__(
        self,
        endpoint,
        token,
        server_id,
        state,
        auth_methods,
        ssh_key_fingerprints,
        ssh_key_name,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.server_id = server_id
        self.state = state
        self.auth_methods = auth_methods
        self._validate_auth_methods(auth_methods, ssh_key_fingerprints, ssh_key_name)
        self.ssh_key_fingerprints = self._resolve_ssh_keys(
            ssh_key_fingerprints, ssh_key_name
        )
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    @staticmethod
    def _validate_auth_methods(auth_methods, ssh_key_fingerprints, ssh_key_name):
        if not auth_methods:
            return
        valid_methods = {"password", "ssh_key"}
        invalid = set(auth_methods) - valid_methods
        if invalid:
            raise ModuleError(
                f"Invalid auth_methods: {', '.join(sorted(invalid))}. "
                f"Valid values are: {', '.join(sorted(valid_methods))}"
            )
        if "ssh_key" in auth_methods and not ssh_key_fingerprints and not ssh_key_name:
            raise ModuleError(
                "ssh_key_fingerprints or ssh_key_name is required "
                "when 'ssh_key' is in auth_methods."
            )

    def _resolve_ssh_keys(self, ssh_key_fingerprints, ssh_key_name):
        if ssh_key_fingerprints:
            return ssh_key_fingerprints
        if not ssh_key_name:
            return None
        return [
            self.api.toolbox.get_ssh_fingerprints_by_key_name(
                ssh_key_name, must=True
            )
        ]

    def _get_rescue_feature_status(self, retry_rules=None):
        features = self.api.get_dedicated_server_features(
            self.server_id, retry_rules=retry_rules
        )
        for feature in features:
            if feature["name"] == "host_rescue_mode":
                return feature["status"]
        raise ModuleError(
            f"host_rescue_mode feature not found for server {self.server_id}. "
            "The server may not support rescue mode."
        )

    def _retry_on_api_error(self, action):
        start = time.time()
        while True:
            try:
                return action()
            except APIError409 as e:
                if '"INCOMPATIBLE_FEATURE_STATE"' not in e.msg:
                    raise
                if time.time() - start > self.wait:
                    raise
                time.sleep(self.update_interval)
            except APIError412:
                if time.time() - start > self.wait:
                    raise
                time.sleep(self.update_interval)

    def _wait_for_feature_status(self, target_status):
        start = time.time()
        while True:
            elapsed = time.time() - start
            status = self._get_rescue_feature_status(
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
            if status == target_status:
                return
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for rescue feature "
                    f"status={target_status}, last={status}",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    def activate_rescue(self):
        feature_status = self._get_rescue_feature_status()

        if feature_status == "unavailable":
            raise ModuleError(
                f"Rescue mode is unavailable for server {self.server_id}."
            )
        if feature_status == "incompatible":
            raise ModuleError(
                f"Rescue mode is incompatible for server {self.server_id}."
            )

        if feature_status == "activated":
            server = self.api.get_dedicated_servers(self.server_id)
            server["changed"] = False
            return server

        if feature_status == "activation":
            if self.wait:
                self._wait_for_feature_status("activated")
            server = self.api.get_dedicated_servers(self.server_id)
            server["changed"] = False
            return server

        if self.checkmode:
            server = self.api.get_dedicated_servers(self.server_id)
            server["changed"] = True
            return server

        self._retry_on_api_error(
            lambda: self.api.post_dedicated_server_rescue_activate(
                self.server_id,
                auth_methods=self.auth_methods,
                ssh_key_fingerprints=self.ssh_key_fingerprints,
            )
        )

        if self.wait:
            self._wait_for_feature_status("activated")
        server = self.api.get_dedicated_servers(self.server_id)
        server["changed"] = True
        return server

    def deactivate_rescue(self):
        feature_status = self._get_rescue_feature_status()

        if feature_status == "unavailable":
            raise ModuleError(
                f"Rescue mode is unavailable for server {self.server_id}."
            )

        if feature_status == "deactivated":
            server = self.api.get_dedicated_servers(self.server_id)
            server["changed"] = False
            return server

        if feature_status == "deactivation":
            if self.wait:
                self._wait_for_feature_status("deactivated")
            server = self.api.get_dedicated_servers(self.server_id)
            server["changed"] = False
            return server

        if self.checkmode:
            server = self.api.get_dedicated_servers(self.server_id)
            server["changed"] = True
            return server

        self._retry_on_api_error(
            lambda: self.api.post_dedicated_server_rescue_deactivate(
                self.server_id
            )
        )

        if self.wait:
            self._wait_for_feature_status("deactivated")
        server = self.api.get_dedicated_servers(self.server_id)
        server["changed"] = True
        return server

    def run(self):
        if self.state == "rescue":
            return self.activate_rescue()
        elif self.state == "normal":
            return self.deactivate_rescue()
        else:
            raise ModuleError(f"Unknown state: {self.state}")
