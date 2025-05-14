from __future__ import absolute_import, division, print_function
import hashlib
from textwrap import wrap
import base64
import time
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    SCBaseError,
    APIError400,
    APIError404,
    APIError409,
    DEFAULT_API_ENDPOINT,
    ScApi,
)

__metaclass__ = type

_ignored = DEFAULT_API_ENDPOINT  # to silence pylint warning, it is reimported

CHANGED = True
NOT_CHANGED = False


class ModuleError(SCBaseError):
    def __init__(self, msg):
        self.msg = msg

    def fail(self):
        return {"failed": True, "msg": self.msg}


class WaitError(ModuleError):
    def __init__(self, msg, timeout):
        self.msg = msg
        self.timeout = timeout

    def fail(self):
        return {"failed": True, "timeout": self.timeout, "msg": self.msg}


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


class ScCloudComputingRegionsInfo(object):
    def __init__(self, endpoint, token, search_pattern):
        self.search_pattern = search_pattern
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

    def regions(self):
        return self.api.list_regions()

    def search(self, regions):
        for region in regions:
            if not self.search_pattern:
                yield region
            else:
                if (
                    self.search_pattern.lower() in region["name"].lower()
                    or self.search_pattern.lower() in region["code"].lower()
                ):
                    yield region

    def run(self):
        ret_data = {"changed": False}
        ret_data["regions"] = list(self.search(self.regions()))
        return ret_data


class ScSshKey(object):
    def __init__(
        self,
        endpoint,
        token,
        state,
        name,
        fingerprint,
        public_key,
        labels,
        replace,
        checkmode,
    ):
        self.partial_match = []
        self.full_match = []
        self.any_match = []
        self.api = ScApi(token, endpoint)
        self.checkmode = checkmode
        self.replace = replace
        self.state = state
        self.key_name = name
        self.public_key = public_key
        self.fingerprint = fingerprint
        self.labels = labels
        if public_key:
            self.fingerprint = self.extract_fingerprint(public_key)
            if fingerprint and self.fingerprint != fingerprint:
                raise ModuleError(msg="Fingerprint does not match public_key")
        if state == "absent":
            if not any([fingerprint, name, public_key]):
                raise ModuleError(
                    "Need at least one of name, fingerprint, public_key "
                    "for state=absent"
                )
        if state == "present":
            if not public_key:
                raise ModuleError("Need public_key for state=present")
            if not name:
                raise ModuleError("Need name for state=present")

    @staticmethod
    def extract_fingerprint(public_key):
        parts = public_key.split()
        # real key is the largest word in the line
        parts.sort(key=len, reverse=True)
        the_key = base64.decodebytes(parts[0].encode("ascii"))
        digest = hashlib.md5(the_key).hexdigest()
        fingerprint = ":".join(wrap(digest, 2))
        return fingerprint

    @staticmethod
    def classify_matching_keys(key_list, name, fingerprint):
        full_match = []
        partial_match = []
        any_match = []
        for key in key_list:
            if key["name"] == name or key["fingerprint"] == fingerprint:
                any_match.append(key)
                if key["name"] == name and key["fingerprint"] == fingerprint:
                    full_match.append(key)
                else:
                    partial_match.append(key)
        return (full_match, partial_match, any_match)

    def add_key(self):
        if not self.checkmode:
            return self.api.post_ssh_keys(
                name=self.key_name, public_key=self.public_key, labels=self.labels
            )

    def delete_keys(self, key_list):
        if not self.checkmode:
            for key in key_list:
                self.api.delete_ssh_keys(fingerprint=key["fingerprint"])

    def state_absent(self):
        if not self.any_match:
            return NOT_CHANGED
        self.delete_keys(self.any_match)
        return CHANGED

    def state_present(self):
        changed = NOT_CHANGED
        if self.full_match and not self.partial_match:
            return NOT_CHANGED
        if self.partial_match and not self.replace:
            raise ModuleError(
                "Error: Partial match found and no replace option. "
                f"Partially matching keys: {repr(self.partial_match)}"
            )
        if self.partial_match and self.replace:
            self.delete_keys(self.partial_match)
            changed = CHANGED
        if not self.full_match:
            self.add_key()
            changed = CHANGED
        return changed

    def run(self):
        (
            self.full_match,
            self.partial_match,
            self.any_match,
        ) = self.classify_matching_keys(
            self.api.list_ssh_keys(), self.key_name, self.fingerprint
        )
        if self.state == "absent":
            changed = self.state_absent()
        if self.state == "present":
            changed = self.state_present()
        return {"changed": changed}


class ScSshKeysInfo:
    def __init__(self, endpoint, token, label_selector):
        self.api = ScApi(token, endpoint)
        self.label_selector = label_selector

    def run(self):
        return {
            "changed": False,
            "ssh_keys": list(self.api.list_ssh_keys(self.label_selector)),
        }


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
                    f"than wait time ({wait}"
                )
        self.api = ScApi(token, endpoint)
        self.old_server_data = None
        self.server_id = server_id
        self.hostname = self.get_hostname(hostname)
        self.drives_layout = self.get_drives_layout(
            drives_layout, drives_layout_template
        )
        self.operating_system_id = self.get_operating_system_id(operating_system_id)
        self.ssh_keys = self.get_ssh_keys(ssh_keys, ssh_key_name)
        self.wait = wait
        self.update_interval = update_interval
        self.user_data = user_data
        self.checkmode = checkmode

    def get_server_data(self):
        if not self.old_server_data:
            self.old_server_data = self.api.get_dedicated_servers(self.server_id)

    def get_hostname(self, hostname):
        if hostname:
            return hostname
        self.get_server_data()
        if "title" not in self.old_server_data:
            raise ModuleError(
                "Unable to retrive old title for the server. "
                "use hostname option to specify the hostname for reinstall."
            )
        return self.old_server_data["title"]

    def get_operating_system_id(self, operating_system_id):
        if operating_system_id:
            return operating_system_id
        self.get_server_data()
        cfg = self.old_server_data.get("configuration_details")
        if not cfg or "operating_system_id" not in cfg:
            raise ModuleError(
                "no operating_system_id was given, and unable to get old"
                "operating_system_id"
            )
        return cfg["operating_system_id"]

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
            {"slot_positions": [0], "raid": 0, "partitions": partitions_template}
        ]
        templates = {"raid1-simple": rai1_simple, "raid0-simple": raid0_simple}
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
            server_info = self.api.get_dedicated_servers(self.server_id)
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


class ScCloudComputingFlavorsInfo:
    def __init__(self, endpoint, token, region_id):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id

    def run(self):
        return {
            "changed": False,
            "cloud_flavors": list(self.api.list_flavors(self.region_id)),
        }


class ScCloudComputingImagesInfo:
    def __init__(self, endpoint, token, region_id):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id

    def run(self):
        return {
            "changed": False,
            "cloud_images": list(self.api.list_images(self.region_id)),
        }


class ScCloudComputingInstancesInfo:
    def __init__(self, endpoint, token, region_id, label_selector):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id
        self.label_selector = label_selector

    def run(self):
        return {
            "changed": False,
            "cloud_instances": list(
                self.api.list_instances(self.region_id, self.label_selector)
            ),
        }


class ScCloudComputingInstanceInfo:
    def __init__(self, endpoint, token, instance_id, name, region_id):
        self.api = ScApi(token, endpoint)
        self.instance_id = self.api.toolbox.find_instance(
            instance_id=instance_id, instance_name=name, region_id=region_id, must=True
        )["id"]

    def run(self):
        result = self.api.get_instances(self.instance_id)
        result["changed"] = False
        return result


class ScCloudComputingOpenstackCredentials:
    def __init__(self, endpoint, token, region_id):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id

    def run(self):
        result = self.api.get_credentials(self.region_id)
        result["changed"] = False
        return result


class ScCloudComputingInstanceCreate:
    def __init__(
        self,
        endpoint,
        token,
        region_id,
        name,
        image_id,
        image_regexp,
        flavor_id,
        flavor_name,
        gpn_enabled,
        ipv4_enabled,
        ipv6_enabled,
        ssh_key_fingerprint,
        ssh_key_name,
        backup_copies,
        user_data,
        labels,
        wait,
        update_interval,
        checkmode,
    ):
        self.checkmode = checkmode
        self.api = ScApi(token, endpoint)
        if region_id is None:
            raise ModuleError("region_id is mandatory for state=present.")
        self.region_id = region_id
        if not name:
            raise ModuleError("Name is mandatory for state=present.")
        self.name = name
        self.instance_id = None
        self.flavor_id = self.get_flavor_id(flavor_id, flavor_name)
        self.image_id = self.api.toolbox.find_image_id(
            image_id=image_id, image_regexp=image_regexp, region_id=region_id, must=True
        )
        self.gpn_enabled = gpn_enabled
        self.ipv4_enabled = ipv4_enabled
        self.ipv6_enabled = ipv6_enabled
        self.ssh_key_fingerprint = self.get_ssh_key_fingerprint(
            ssh_key_fingerprint, ssh_key_name
        )
        self.backup_copies = backup_copies
        self.user_data = user_data
        self.labels = labels
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def get_ssh_key_fingerprint(self, ssh_key_fingerprint, ssh_key_name):
        if ssh_key_fingerprint:
            return ssh_key_fingerprint
        if ssh_key_name:
            for key in self.api.list_ssh_keys():
                if key["name"] == ssh_key_name:
                    return key["fingerprint"]
            raise ModuleError(f"Unable to find ssh key {ssh_key_name}")
        return None

    def get_flavor_id(self, flavor_id, flavor_name):
        if flavor_id and flavor_name:
            raise ModuleError("Both flavor_id and flavor_name are present.")
        if not flavor_id and not flavor_name:
            raise ModuleError("Need either flavor_id or flavor_name.")
        if flavor_name:
            flavor_id = self.api.toolbox.find_cloud_flavor_id_by_name(
                flavor_name=flavor_name, region_id=self.region_id, must=True
            )
        return flavor_id

    def create_instance(self):
        instance = self.api.post_instance(
            region_id=self.region_id,
            name=self.name,
            flavor_id=self.flavor_id,
            image_id=self.image_id,
            gpn_enabled=self.gpn_enabled,
            ipv4_enabled=self.ipv4_enabled,
            ipv6_enabled=self.ipv6_enabled,
            ssh_key_fingerprint=self.ssh_key_fingerprint,
            backup_copies=self.backup_copies,
            user_data=self.user_data,
            labels=self.labels,
        )
        return instance

    def wait_for(self, instance):
        start_time = time.time()
        instance = self.api.get_instances(instance["id"])
        if not self.wait:
            return instance
        while instance["status"] != "ACTIVE":
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout while waiting instance {instance['id']}"
                    f" to become ACTIVE. Last status was {instance['status']}",
                    timeout=elapsed,
                )
            instance = self.api.get_instances(instance["id"])
        return instance

    def run(self):
        instance = self.api.toolbox.find_instance(
            self.instance_id, self.name, self.region_id, must=False
        )
        if instance:
            instance["changed"] = NOT_CHANGED
        else:
            if not self.checkmode:
                instance = self.create_instance()
                instance = self.wait_for(instance)
            else:
                instance = {
                    "info": "Instance shold be created, "
                    "but check_mode is activated. "
                    "no real instance was created."
                }
            instance["changed"] = CHANGED
        return instance


class ScCloudComputingInstanceDelete:
    def __init__(
        self,
        endpoint,
        token,
        instance_id,
        region_id,
        name,
        wait,
        update_interval,
        retry_on_conflicts,
        checkmode,
    ):
        self.checkmode = checkmode
        self.api = ScApi(token, endpoint)
        self.region_id = region_id
        self.name = name
        self.instance_id = instance_id
        if update_interval > wait:
            raise ModuleError(
                f"update interval ({update_interval}) " f"is longer than wait ({wait})"
            )
        self.wait = wait
        self.update_interval = update_interval
        self.retry_on_conflicts = retry_on_conflicts

    def wait_for_disappearance(self):
        start_time = time.time()
        instance = self.api.toolbox.find_instance(
            self.instance_id, self.name, self.region_id, must=False
        )
        while instance:
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout while waiting instance {instance['id']}"
                    f" to disappear. Last status was {instance['status']}",
                    timeout=elapsed,
                )
            instance = self.api.toolbox.find_instance(
                self.instance_id, self.name, self.region_id, must=False
            )

    def retry_to_delete(self, instance):
        # pylint: disable=bad-option-value, raise-missing-from
        start_time = time.time()
        while instance:
            try:
                self.api.delete_instance(instance["id"])

            except APIError409:
                if self.retry_on_conflicts:
                    elapsed = time.time() - start_time
                    if elapsed > self.wait:
                        raise WaitError(
                            msg="Timeout retrying delete for"
                            f' instance {instance["id"]}',
                            timeout=elapsed,
                        )
                    time.sleep(self.update_interval)
                else:
                    raise
            except APIError404:
                # We expected to delete instance and it's gone
                # == happy end
                pass
            instance = instance = self.api.toolbox.find_instance(
                self.instance_id, self.name, self.region_id, must=False
            )

    def run(self):
        # pylint: disable=bad-option-value, raise-missing-from
        original_instance = self.api.toolbox.find_instance(
            self.instance_id, self.name, self.region_id, must=False
        )
        instance = original_instance
        if not instance:
            return {
                "changed": False,
                "instance_id": self.instance_id,
                "name": self.name,
                "region_id": self.region_id,
            }
        if not self.checkmode:
            instance = self.retry_to_delete(instance)
            self.wait_for_disappearance()
        original_instance["changed"] = CHANGED
        return original_instance


class ScCloudComputingInstancePtr:
    def __init__(
        self,
        endpoint,
        token,
        state,
        instance_id,
        name,
        region_id,
        ip,
        domain,
        ttl,
        priority,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.state = state
        self.instance_id = instance_id
        self.name = name
        self.region_id = region_id
        self.ip = ip
        self.domain = domain
        self.ttl = ttl
        self.priority = priority
        self.checkmode = checkmode

    def find_ptr(self, ptr_records, domain, ip):
        for record in ptr_records:
            found = False
            if domain and domain == record["domain"]:
                found = True
            if ip and ip == record["ip"]:
                found = True
            if found:
                yield record

    def run(self):
        instance = self.api.toolbox.find_instance(
            instance_id=self.instance_id,
            instance_name=self.name,
            region_id=self.region_id,
            must=True,
        )
        ptr_records = list(self.api.list_instance_ptr_records(instance["id"]))
        if self.state == "query":
            return {"changed": False, "ptr_records": list(ptr_records)}
        elif self.state == "present":
            if list(self.find_ptr(ptr_records, self.domain, self.ip)):
                return {"changed": False, "ptr_records": list(ptr_records)}
            if self.checkmode:
                return {"changed": True, "ptr_records": list(ptr_records)}
            self.api.post_instance_ptr_records(
                instance_id=instance["id"],
                data=self.domain,
                ip=self.ip,
                ttl=self.ttl,
                priority=self.priority,
            )
            return {
                "changed": True,
                "ptr_records": list(self.api.list_instance_ptr_records(instance["id"])),
            }
        elif self.state == "absent":
            if not list(self.find_ptr(ptr_records, self.domain, self.ip)):
                return {"changed": False, "ptr_records": list(ptr_records)}
            if self.checkmode:
                return {"changed": True, "ptr_records": list(ptr_records)}
            for record in self.find_ptr(ptr_records, self.domain, self.ip):
                self.api.delete_instance_ptr_records(
                    instance_id=instance["id"], record_id=record["id"]
                )
            return {
                "changed": True,
                "ptr_records": list(self.api.list_instance_ptr_records(instance["id"])),
            }
        else:
            raise ModuleError(f"Unknown state={self.state}")


class ScCloudComputingInstanceState:
    def __init__(
        self,
        endpoint,
        token,
        state,
        instance_id,
        name,
        region_id,
        image_id,
        image_regexp,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.state = state
        self.instance_id = self.api.toolbox.find_instance(
            instance_id=instance_id, instance_name=name, region_id=region_id, must=True
        )["id"]
        self.image_id = image_id
        self.image_regexp = image_regexp
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def wait_for_statuses(self, status_done, statuses_continue):
        start_time = time.time()
        while self.instance["status"] not in statuses_continue + [status_done]:
            if not self.wait:
                break
            if time.time() > start_time + self.wait:
                raise WaitError(
                    msg=f"Timeout waiting instance {self.instance['id']} "
                    f"status {status_done} or {statuses_continue}. "
                    f"Last state was {self.instance['status']}",
                    timeout=time.time() - start_time,
                )
            time.sleep(self.update_interval)
            self.instance = self.api.get_instances(self.instance_id)
        if self.instance["status"] == status_done:
            return True
        else:
            if self.instance["status"] in statuses_continue:
                return False
            else:
                if self.wait:
                    raise WaitError(
                        msg=f"Timeout waiting instance {self.instance['id']} "
                        f"status {status_done}. "
                        f"Last state was {self.instance['status']}",
                        timeout=time.time() - start_time,
                    )

    def shutdown(self):
        if self.instance["status"] == "RESCUE":
            raise ModuleError("Shutdown is not supported in rescue mode.")
        if self.wait_for_statuses(
            status_done="SWITCHED_OFF", statuses_continue=["ACTIVE"]
        ):
            self.instance["changed"] = False
            return self.instance
        if self.checkmode:
            self.instance["changed"] = True
            return self.instance
        self.api.post_instance_switch_off(self.instance_id)
        self.wait_for_statuses(status_done="SWITCHED_OFF", statuses_continue=[])
        self.instance = self.api.get_instances(self.instance_id)
        self.instance["changed"] = True
        return self.instance

    def normalize(self):
        if self.wait_for_statuses(
            status_done="ACTIVE", statuses_continue=["SWITCHED_OFF", "RESCUE"]
        ):
            self.instance["changed"] = False
            return self.instance
        if self.checkmode:
            self.instance["changed"] = True
            return self.instance
        if self.instance["status"] == "SWITCHED_OFF":
            self.api.post_instance_switch_on(self.instance_id)
        elif self.instance["status"] == "RESCUE":
            self.api.post_instance_unrescue(self.instance_id)
        self.wait_for_statuses(status_done="ACTIVE", statuses_continue=[])
        self.instance = self.api.get_instances(self.instance_id)
        self.instance["changed"] = True
        return self.instance

    def rescue(self):
        if self.image_id or self.image_regexp:
            image_id = self.api.toolbox.find_image_id(
                image_id=self.image_id,
                image_regexp=self.image_regexp,
                region_id=self.instance["region_id"],
                must=True,
            )
        else:
            image_id = None
        if self.wait_for_statuses(
            status_done="RESCUE", statuses_continue=["ACTIVE", "SWITCHED_OFF"]
        ):
            self.instance["changed"] = False
            return self.instance
        if self.checkmode:
            self.instance["changed"] = True
            return self.instance
        self.api.post_instance_rescue(self.instance_id, image_id)
        self.wait_for_statuses(status_done="RESCUE", statuses_continue=[])
        self.instance = self.api.get_instances(self.instance_id)
        self.instance["changed"] = True
        return self.instance

    def reboot(self):
        raise NotImplementedError

    def run(self):
        self.instance = self.api.get_instances(self.instance_id)
        if self.state == "shutdown":
            return self.shutdown()
        elif self.state == "rescue":
            return self.rescue()
        elif self.state == "rebooted":
            return self.reboot()
        elif self.state == "normal":
            return self.normalize()
        else:
            raise ModuleError(f"Unknown state={self.state}")


class ScCloudComputingInstanceReinstall:
    def __init__(
        self,
        endpoint,
        token,
        instance_id,
        name,
        region_id,
        image_id,
        image_regexp,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.instance = self.api.toolbox.find_instance(
            instance_id=instance_id, instance_name=name, region_id=region_id, must=True
        )
        if not image_id and not image_regexp:
            self.image_id = self.instance["image_id"]
        else:
            self.image_id = self.api.toolbox.find_image_id(
                image_id=image_id, image_regexp=image_regexp, region_id=region_id
            )
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    #  copypaste, refactor, TODO
    def wait_for_statuses(self, status_done, statuses_continue):
        start_time = time.time()
        if self.wait:
            time.sleep(self.update_interval)  # workaround around bug in APIs
        while self.instance["status"] not in statuses_continue + [status_done]:
            if not self.wait:
                break
            if time.time() > start_time + self.wait:
                raise WaitError(
                    msg=f"Timeout waiting instance {self.instance['id']} "
                    f"status {status_done} or {statuses_continue}. "
                    f"Last state was {self.instance['status']}",
                    timeout=time.time() - start_time,
                )
            time.sleep(self.update_interval)
            self.instance = self.api.get_instances(self.instance["id"])
        if self.instance["status"] == status_done:
            return True
        else:
            if self.instance["status"] in statuses_continue:
                return False
            else:
                if self.wait:
                    raise WaitError(
                        msg=f"Timeout waiting instance {self.instance['id']} "
                        f"status {status_done}. "
                        f"Last state was {self.instance['status']}",
                        timeout=time.time() - start_time,
                    )

    def run(self):
        if self.checkmode:
            self.instance["changed"] = True
            return self.instance
        self.api.post_instances_reinstall(
            instance_id=self.instance["id"], image_id=self.image_id
        )
        self.wait_for_statuses(status_done="ACTIVE", statuses_continue=[])
        self.instance["changed"] = True
        return self.instance


class ScCloudComputingInstanceUpgrade:
    def __init__(
        self,
        endpoint,
        token,
        instance_id,
        name,
        region_id,
        flavor_id,
        flavor_name,
        confirm_upgrade,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.instance = self.api.toolbox.find_instance(
            instance_id=instance_id, instance_name=name, region_id=region_id, must=True
        )
        self.flavor_id = self.api.toolbox.find_cloud_flavor_id_by_name(
            flavor_id=flavor_id, flavor_name=flavor_name, region_id=region_id
        )
        self.confirm_upgrade = confirm_upgrade
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def run(self):
        if self.flavor_id == self.instance["flavor_id"]:
            self.instance["changed"] = False
            return self.instance
        if self.checkmode:
            self.instance["changed"] = True
            return self.instance
        raise NotImplementedError()
        # self.api.post_instances_approve_upgrade(self.instance['id'])
        #     self.wait_for_statuses(
        #         status_done = 'ACTIVE',
        #         statuses_continue = []
        #     )


class ScL2SegmentsInfo:
    def __init__(self, endpoint, token, label_selector):
        self.api = ScApi(token, endpoint)
        self.label_selector = label_selector

    def run(self):
        return {
            "changed": False,
            "l2_segments": list(self.api.list_l2_segments(self.label_selector)),
        }


class ScL2SegmentInfo:
    def __init__(self, endpoint, token, id, name):
        self.api = ScApi(token, endpoint)
        self.id = id
        self.name = name

    def run(self):
        id = self.id
        if self.name:
            for segment in self.api.list_l2_segments():
                if segment["name"] == self.name:
                    if id:
                        raise ModuleError(
                            "Multiple segments with the same name found. Use id."
                        )
                    id = segment["id"]
            if not id:  # Either ID is from args, or we found it, or it can't be found
                raise ModuleError(f"Unable to find segment with name {self.name}")
        networks = list(self.api.list_l2_segment_networks(id))
        members = list(self.api.list_l2_segment_members(id))
        l2_segment = self.api.get_l2_segment(id)
        l2_segment["networks"] = networks
        l2_segment["members"] = members
        return {"changed": False, "l2_segment": l2_segment}


class ScL2Segment:
    def __init__(
        self,
        endpoint,
        token,
        name,
        segment_id,
        state,
        type,
        members,
        members_present,
        members_absent,
        location_group_id,
        labels,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.name = name
        self.segment_id = segment_id
        self.state = state
        self.type = type
        self.members = members
        self.members_present = members_present
        self.members_absent = members_absent
        self.location_group_id = location_group_id
        self.labels = labels
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode
        if update_interval > wait:
            raise ModuleError("update_interval is longer than wait")

    @staticmethod
    def _match_segment(api_object, segment_name, type):
        if type:
            return api_object["name"] == segment_name and api_object["type"] == type
        else:
            return api_object["name"] == segment_name

    def get_segment_id(self):
        existing_segment_id = None
        if self.segment_id:
            existing_segment_id = self.api.get_l2_segment_or_none(self.segment_id)["id"]
        else:
            for segment in self.api.list_l2_segments():
                if self._match_segment(segment, self.name, self.type):
                    if existing_segment_id:  # duplicate found
                        raise ModuleError(
                            msg=f"Duplicate segment with name {self.name} found."
                        )
                    existing_segment_id = segment["id"]
        return existing_segment_id

    def wait_for_active_segment(self, segment_id):
        ready = False
        start_time = time.time()
        elapsed = 0
        while not ready:
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(msg="Segment is not ready.", timeout=elapsed)
            segment = self.api.get_l2_segment(segment_id)
            ready = segment["status"] == "active"

    def wait_for_segment_disappear(self, segment_id):
        ready = False
        start_time = time.time()
        elapsed = 0
        while not ready:
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(msg="Segment is not deleted.", timeout=elapsed)
            segment = self.api.get_l2_segment_or_none(segment_id)
            ready = not segment["id"]

    def guess_member_location_groups(self, members):
        locations = set()
        suitable_location_groups = set()
        for member in members:
            srv = self.api.get_dedicated_servers(member["id"])
            locations.add(srv["location_id"])
        for location_group in self.api.list_l2_location_groups():
            if (
                locations.issubset(set(location_group["location_ids"]))
                and location_group["group_type"] == self.type
            ):
                suitable_location_groups.add(location_group["id"])
        if not suitable_location_groups:
            raise ModuleError(
                f"Unable to find location group for all members in locations: {repr(locations)}"
            )
        return suitable_location_groups

    def get_member_location_group_id(self, members):
        member_guessed_lgs = self.guess_member_location_groups(members)
        if self.location_group_id:
            if self.location_group_id in member_guessed_lgs:
                return self.location_group_id
            raise ModuleError(
                f"location_group_id {self.location_group_id} is not compatible with members locations."
            )
        if len(member_guessed_lgs) > 1:
            raise ModuleError(
                f"More than one location group is suitable for members: {member_guessed_lgs}, use location_group_id parameter."
            )
        return member_guessed_lgs.pop()  # only one is in the set

    def create(self):
        members = (
            self.members or self.members_present
        )  # we can ignore members_absent for create mode
        lg = self.get_member_location_group_id(members)
        if not self.name:
            raise ModuleError("Creation of L2 segment required name")
        if not self.type:
            raise ModuleError("Creation of L2 segment required type")
        if self.checkmode:
            return {"changed": True, "location_group_id": lg}
        res = self.api.post_l2_segment(self.name, self.type, lg, members, self.labels)
        self.wait_for_active_segment(res["id"])
        res = self.api.get_l2_segment(res["id"])
        res["members_added"] = members
        res["members_removed"] = []
        res["changed"] = True
        return res

    @staticmethod
    def _listdict_to_set(iterable):
        return set([tuple(d.items()) for d in iterable or []])

    @staticmethod
    def _set_to_listdict(s):
        return [dict(tup) for tup in s]

    @staticmethod
    def _simplify_members(iterable):
        for m in iterable:
            yield {"id": m["id"], "mode": m["mode"]}

    def update_full(self, segment_id):
        changed = False
        members_lg = self.get_member_location_group_id(self.members)
        segment = self.api.get_l2_segment(segment_id)
        if members_lg != segment["location_group_id"]:
            raise ModuleError(
                f"members location group {members_lg} does not match location group for existing segment: {segment['location_group_id']}"
            )
        existing_members = self._listdict_to_set(
            self._simplify_members(self.api.list_l2_segment_members(segment_id))
        )
        new_members = self._listdict_to_set(self.members)
        keep_members = existing_members & new_members
        del_list = self._set_to_listdict(existing_members - new_members)
        keep_list = self._set_to_listdict(keep_members)
        add_list = self._set_to_listdict(new_members - existing_members)
        if del_list or add_list:
            changed = True
            if not self.checkmode:
                if keep_members != existing_members:
                    self.api.put_l2_segment_update(segment_id, keep_list, self.labels)
                    self.wait_for_active_segment(segment_id)
                self.api.put_l2_segment_update(segment_id, self.members, self.labels)
                self.wait_for_active_segment(segment_id)
        res = self.api.get_l2_segment(segment_id)
        res["members_added"] = list(add_list)
        res["members_kept"] = list(keep_list)
        res["members_removed"] = list(del_list)
        res["changed"] = changed
        return res

    @staticmethod
    def prep_present_list(members):
        for member in members or []:
            if "mode" in member:
                yield member
            else:
                yield {"id": member["id"], "mode": "native"}

    @staticmethod
    def prep_absent_list(members, old_members):
        for member in members:
            for old_member in old_members:
                if old_member["id"] == member["id"]:
                    yield old_member
                    break
            else:
                yield member  # keep None because it's not in the old_members anyway

    def update_partial(self, segment_id):
        changed = False
        segment = self.api.get_l2_segment(segment_id)
        if self.members_present:
            members_lg = self.get_member_location_group_id(self.members_present)
            if members_lg != segment["location_group_id"]:
                raise ModuleError(
                    f"members location group {members_lg} does not match location group for existing segment: {segment['location_group_id']}"
                )
        old_list = list(
            self._simplify_members(self.api.list_l2_segment_members(segment_id))
        )
        existing_members = self._listdict_to_set(old_list)
        members_present = self._listdict_to_set(
            self.prep_present_list(self.members_present)
        )
        members_absent = self._listdict_to_set(
            self.prep_absent_list(self.members_absent, old_list)
        )
        resulting_members = (existing_members | members_present) - members_absent
        del_list = self._set_to_listdict(existing_members - resulting_members)
        add_list = self._set_to_listdict(resulting_members - existing_members)
        send_list = self._set_to_listdict(resulting_members)
        reduced_list = self._set_to_listdict(existing_members - members_absent)
        if resulting_members != existing_members:
            changed = True
            if not self.checkmode:
                # If member is already with one type and is in members_present with
                # different type we need to remove it first (API requirement)
                if del_list and add_list:
                    self.api.put_l2_segment_update(
                        segment_id, reduced_list, self.labels
                    )
                    self.wait_for_active_segment(segment_id)
                self.api.put_l2_segment_update(segment_id, send_list, self.labels)
                self.wait_for_active_segment(segment_id)
        res = self.api.get_l2_segment(segment_id)
        res["members_added"] = list(add_list)
        res["members_removed"] = list(del_list)
        res["members_kept"] = list(reduced_list)
        res["changed"] = changed
        return res

    def absent(self):
        found_segment_id = self.get_segment_id()
        if found_segment_id:
            if not self.checkmode:
                self.api.delete_l2_segment(found_segment_id)
                self.wait_for_segment_disappear(found_segment_id)
            return {"changed": True, "id": found_segment_id}
        else:
            return {"changed": False}

    def present(self):
        found_segment_id = self.get_segment_id()
        if found_segment_id:
            if self.members_present or self.members_absent:
                return self.update_partial(found_segment_id)
            return self.update_full(found_segment_id)
        else:
            return self.create()

    def run(self):
        if self.state == "absent":
            return self.absent()
        else:  # present
            return self.present()


class ScL2SegmentAliases:
    def __init__(
        self,
        endpoint,
        token,
        name,
        segment_id,
        count,
        aliases_absent,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.name = name
        self.segment_id = segment_id
        self.count = count
        self.aliases_absent = aliases_absent
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    # TODO: code repeated from ScL2Segment
    def get_segment_id(self):
        existing_segment_id = None
        if self.segment_id:
            existing_segment_id = self.api.get_l2_segment(self.segment_id)["id"]
        else:
            for segment in self.api.list_l2_segments():
                if segment["name"] == self.name:
                    if existing_segment_id:  # duplicate found
                        raise ModuleError(
                            msg=f"Duplicate segment with name {self.name} found."
                        )
                    existing_segment_id = segment["id"]
            if not existing_segment_id:
                raise ModuleError(f"Segment {self.name} is not found.")
        return existing_segment_id

    def wait_for(self, l2):
        start_time = time.time()
        if not self.wait:
            return
        while l2["status"] == "pending":
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout while waiting for L2 {l2['id']}."
                    f" Last status was {l2['status']}",
                    timeout=elapsed,
                )
            l2 = self.api.get_l2_segment(l2["id"])

    def prep_result(self, changed):
        aliases = list(self.api.list_l2_segment_networks(self.found_segment_id))
        ipv4_list = [
            alias["cidr"].split("/")[0]
            for alias in aliases
            if alias["family"] == "ipv4"
        ]
        ipv6_list = [
            alias["cidr"].split("/")[0]
            for alias in aliases
            if alias["family"] == "ipv6"
        ]
        return {
            "changed": changed,
            "aliases": aliases,
            "aliases_count": len(aliases),
            "ipv4_list": ipv4_list,
            "ipv6_list": ipv6_list,
            "id": self.found_segment_id,
        }

    def add_aliases(self, add_count):
        if not self.checkmode:
            create_array = [{"mask": 32, "distribution_method": "route"}] * add_count
            res = self.api.put_l2_segment_networks(
                self.found_segment_id, create=create_array, delete=[]
            )
            self.wait_for(res)
        return self.prep_result(True)

    @staticmethod
    def extract_ids(aliases):
        return [alias["id"] for alias in aliases]

    @staticmethod
    def get_del_list(aliases_existing_ids, aliases_absent_ids):
        return list(set(aliases_absent_ids) & set(aliases_existing_ids))

    def remove_aliases(self, to_remove_ids):
        changed = False
        del_list = self.get_del_list(self.existing_aliases_id, to_remove_ids)
        if del_list:
            changed = True
            if not self.checkmode:
                res = self.api.put_l2_segment_networks(
                    self.found_segment_id, create=[], delete=del_list
                )
                self.wait_for(res)
        return self.prep_result(changed)

    def set_count(self):
        changed = False
        if len(self.existing_aliases) < self.count:
            return self.add_aliases(self.count - len(self.existing_aliases_id))
        elif len(self.existing_aliases) > self.count:
            return self.remove_aliases(self.existing_aliases_id[self.count :])
        return self.prep_result(changed)

    def run(self):
        self.found_segment_id = self.get_segment_id()
        self.existing_aliases = list(
            self.api.list_l2_segment_networks(self.found_segment_id)
        )
        self.existing_aliases_id = self.extract_ids(self.existing_aliases)
        if self.aliases_absent:
            return self.remove_aliases(self.aliases_absent)
        else:
            if self.count is None:
                raise ModuleError("Count must not be None")
            return self.set_count()


class ScLoadBalancerInstancesList:
    def __init__(self, endpoint, token, name=None, type=None, label_selector=None):
        self.api = ScApi(token, endpoint)
        self.name = name
        self.type = type
        self.label_selector = label_selector

    def run(self):
        lb_instances = list(self.api.list_load_balancer_instances(self.label_selector))
        if self.name:
            lb_instances = [
                inst for inst in lb_instances if inst.get("name") == self.name
            ]
        if self.type:
            lb_instances = [
                inst for inst in lb_instances if inst.get("type") == self.type
            ]
        return {
            "changed": False,
            "load_balancer_instances": lb_instances,
        }


class ScLoadBalancerInstanceInfo(object):
    def __init__(
        self, endpoint, token, lb_instance_id, lb_instance_name, fail_on_absent
    ):
        self.api = ScApi(token, endpoint)
        self.fail_on_absent = fail_on_absent
        if lb_instance_id and lb_instance_name:
            raise ValueError("Only one of 'id' or 'name' should be provided")
        self.lb_instance_id = lb_instance_id
        self.lb_instance_name = lb_instance_name

    def run(self):
        lb_instances = self.api.list_load_balancer_instances()
        target_instance = None

        if self.lb_instance_id:
            target_instance = next(
                (
                    inst
                    for inst in lb_instances
                    if inst.get("id") == self.lb_instance_id
                ),
                None,
            )
        elif self.lb_instance_name:
            matched_instances = [
                inst
                for inst in lb_instances
                if inst.get("name") == self.lb_instance_name
            ]
            if len(matched_instances) > 1:
                instance_ids = ", ".join(inst.get("id") for inst in matched_instances)
                raise ModuleError(
                    msg=f"There are more than one instance with the specified name: {instance_ids}. Such configuration doesn't support by the module."
                )
            elif matched_instances:
                target_instance = matched_instances[0]

        if not target_instance:
            if self.fail_on_absent:
                raise ModuleError(msg="Load balancer instance not found")
            return {"changed": False, "status": "absent"}

        lb_id = target_instance.get("id")
        lb_type = target_instance.get("type")

        try:
            lb_instance_info = self.api.get_lb_instance(lb_id, lb_type)
        except (APIError404, APIError400) as e:
            if self.fail_on_absent:
                raise e
            return {"changed": False, "status": "absent"}

        lb_instance_info["changed"] = False
        return lb_instance_info


class ScLbInstanceDelete:
    def __init__(
        self,
        endpoint,
        token,
        lb_type,
        lb_id=None,
        lb_name=None,
        wait=600,
        update_interval=5,
        checkmode=False,
    ):
        if lb_id and lb_name:
            raise ValueError("Only one of 'id' or 'name' should be provided")
        if not lb_id and not lb_name:
            raise ValueError("Either 'id' or 'name' must be provided")
        self.checkmode = checkmode
        self.api = ScApi(token, endpoint)
        self.lb_instance_id = lb_id
        self.lb_instance_name = lb_name
        self.lb_instance_type = lb_type
        self.wait = wait
        self.update_interval = update_interval

    def wait_for_disappearance(self):
        start_time = time.time()
        while True:
            instances = self.api.list_load_balancer_instances()
            exists = any(
                inst.get("id") == self.lb_instance_id
                for inst in instances
                if inst.get("type") == self.lb_instance_type
            )
            if not exists:
                break
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for lb instance {self.lb_instance_id} to disappear after {elapsed:.2f} seconds.",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    def run(self):
        lb_instances = self.api.list_load_balancer_instances()

        if self.lb_instance_id:
            matched_instances = [
                inst
                for inst in lb_instances
                if inst.get("id") == self.lb_instance_id
                and inst.get("type") == self.lb_instance_type
            ]
        elif self.lb_instance_name:
            matched_instances = [
                inst
                for inst in lb_instances
                if inst.get("name") == self.lb_instance_name
                and inst.get("type") == self.lb_instance_type
            ]

        if len(matched_instances) > 1:
            instance_ids = ", ".join(inst.get("id") for inst in matched_instances)
            raise ModuleError(
                msg=f"There are more than one instance with the specified name: {instance_ids}. Such configuration is not supported by the module."
            )
        elif matched_instances:
            instance = matched_instances[0]
            self.lb_instance_id = instance.get("id")
        else:
            instance = None

        if not instance:
            return {
                "changed": False,
                "status": "absent",
                "identifier": self.lb_instance_name or self.lb_instance_id,
            }

        if not self.checkmode:
            self.api.delete_lb_instance(self.lb_instance_id, self.lb_instance_type)
            self.wait_for_disappearance()

        instance["changed"] = True
        instance["status"] = "absent"
        return instance


class ScLbInstanceL4CreateUpdate:
    def __init__(
        self,
        endpoint,
        token,
        lb_id,
        name,
        location_id,
        cluster_id,
        store_logs,
        store_logs_region_id,
        new_external_ips_count,
        delete_external_ips,
        shared_cluster,
        vhost_zones,
        upstream_zones,
        labels,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.lb_instance_id = lb_id
        self.name = name
        self.location_id = location_id
        self.cluster_id = cluster_id
        self.store_logs = store_logs
        self.store_logs_region_id = store_logs_region_id
        self.new_external_ips_count = new_external_ips_count
        self.delete_external_ips = delete_external_ips
        self.shared_cluster = shared_cluster
        self.vhost_zones = vhost_zones
        self.upstream_zones = upstream_zones
        self.labels = labels
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode
        self.lb_instance_type = "l4"

    def get_matching_lb_instances(self):
        lb_instances = self.api.list_load_balancer_instances()
        return [
            inst
            for inst in lb_instances
            if inst.get("type") == self.lb_instance_type
            and inst.get("name") == self.name
        ]

    def update_instance(self):
        return self.api.lb_instance_l4_update(
            lb_id=self.lb_instance_id,
            name=self.name,
            store_logs=self.store_logs,
            store_logs_region_id=self.store_logs_region_id,
            new_external_ips_count=self.new_external_ips_count,
            delete_external_ips=self.delete_external_ips,
            cluster_id=self.cluster_id,
            shared_cluster=self.shared_cluster,
            vhost_zones=self.vhost_zones,
            upstream_zones=self.upstream_zones,
            labels=self.labels,
        )

    def create_instance(self):
        return self.api.lb_instance_l4_create(
            name=self.name,
            location_id=self.location_id,
            cluster_id=self.cluster_id,
            store_logs=self.store_logs,
            store_logs_region_id=self.store_logs_region_id,
            vhost_zones=self.vhost_zones,
            upstream_zones=self.upstream_zones,
            labels=self.labels,
        )

    def wait_for_active(self):
        start_time = time.time()
        while True:
            instance = self.api.get_lb_instance(
                self.lb_instance_id, self.lb_instance_type
            )
            if instance["status"] == "active":
                return instance
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for lb instance {self.lb_instance_id} to become active after {elapsed:.2f} seconds.",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    def check_update_result(self, current):
        if not self.checkmode:
            status_code = self.update_instance()[0]
            updated = self.wait_for_active()
            if status_code == 200:
                updated["changed"] = False
                return updated
            elif status_code == 202:
                updated["changed"] = True
                return updated
        else:
            current["changed"] = False
            return current

    def run(self):
        if self.lb_instance_id:
            current = self.api.get_lb_instance(
                self.lb_instance_id, self.lb_instance_type
            )

            if not current:
                raise ModuleError(
                    msg=f"Load balancer instance with id '{self.lb_instance_id}' not found."
                )
            return self.check_update_result(current)

        matching = self.get_matching_lb_instances()
        if len(matching) > 1:
            instance_ids = [inst["id"] for inst in matching]
            raise ModuleError(
                msg=f"Ambiguous configuration: More than one L4 load balancer instance with the name '{self.name}' exists. Found IDs: {', '.join(instance_ids)}"
            )
        elif len(matching) == 1:
            self.lb_instance_id = matching[0].get("id")
            current = self.api.get_lb_instance(
                self.lb_instance_id, self.lb_instance_type
            )
            return self.check_update_result(current)
        else:
            if not self.checkmode:
                response = self.create_instance()
                self.lb_instance_id = response.get("id")
                new_instance = self.wait_for_active()
                new_instance["changed"] = True
                return new_instance
            else:
                return {"changed": False}


class ScLbInstanceL7CreateUpdate:
    def __init__(
        self,
        endpoint,
        token,
        lb_id,
        name,
        location_id,
        cluster_id,
        store_logs,
        store_logs_region_id,
        geoip,
        vhost_zones,
        upstream_zones,
        labels,
        new_external_ips_count,
        delete_external_ips,
        shared_cluster,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.lb_instance_id = lb_id
        self.name = name
        self.location_id = location_id
        self.cluster_id = cluster_id
        self.store_logs = store_logs
        self.store_logs_region_id = store_logs_region_id
        self.geoip = geoip
        self.vhost_zones = vhost_zones
        self.upstream_zones = upstream_zones
        self.labels = labels
        self.new_external_ips_count = new_external_ips_count
        self.delete_external_ips = delete_external_ips
        self.shared_cluster = shared_cluster
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode
        self.lb_instance_type = "l7"

    def get_matching_lb_instances(self):
        lb_instances = self.api.list_load_balancer_instances()
        return [
            inst
            for inst in lb_instances
            if inst.get("type") == self.lb_instance_type
            and inst.get("name") == self.name
        ]

    def update_instance(self):
        return self.api.lb_instance_l7_update(
            lb_id=self.lb_instance_id,
            name=self.name,
            store_logs=self.store_logs,
            store_logs_region_id=self.store_logs_region_id,
            new_external_ips_count=self.new_external_ips_count,
            delete_external_ips=self.delete_external_ips,
            cluster_id=self.cluster_id,
            shared_cluster=self.shared_cluster,
            geoip=self.geoip,
            vhost_zones=self.vhost_zones,
            upstream_zones=self.upstream_zones,
            labels=self.labels,
        )

    def create_instance(self):
        return self.api.lb_instance_l7_create(
            name=self.name,
            location_id=self.location_id,
            cluster_id=self.cluster_id,
            store_logs=self.store_logs,
            store_logs_region_id=self.store_logs_region_id,
            geoip=self.geoip,
            vhost_zones=self.vhost_zones,
            upstream_zones=self.upstream_zones,
            labels=self.labels,
        )

    def wait_for_active(self):
        start_time = time.time()
        while True:
            instance = self.api.get_lb_instance(
                self.lb_instance_id, self.lb_instance_type
            )
            if instance["status"] == "active":
                return instance
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for lb instance {self.lb_instance_id} to become active after {elapsed:.2f} seconds.",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)

    def check_update_result(self, current):
        if not self.checkmode:
            status_code = self.update_instance()[0]
            updated = self.wait_for_active()
            if status_code == 200:
                updated["changed"] = False
                return updated
            elif status_code == 202:
                updated["changed"] = True
                return updated
        else:
            current["changed"] = False
            return current

    def run(self):
        if self.lb_instance_id:
            current = self.api.get_lb_instance(
                self.lb_instance_id, self.lb_instance_type
            )
            if not current:
                raise ModuleError(
                    msg=f"Load balancer instance with id '{self.lb_instance_id}' not found."
                )
            return self.check_update_result(current)

        matching = self.get_matching_lb_instances()
        if len(matching) > 1:
            instance_ids = [inst["id"] for inst in matching]
            raise ModuleError(
                msg=f"Ambiguous configuration: More than one L7 load balancer instance with the name '{self.name}' exists. Found IDs: {', '.join(instance_ids)}"
            )
        elif len(matching) == 1:
            self.lb_instance_id = matching[0].get("id")
            current = self.api.get_lb_instance(
                self.lb_instance_id, self.lb_instance_type
            )
            return self.check_update_result(current)
        else:
            if not self.checkmode:
                response = self.create_instance()
                self.lb_instance_id = response.get("id")
                new_instance = self.wait_for_active()
                new_instance["changed"] = True
                return new_instance
            else:
                return {"changed": False}
