from __future__ import absolute_import, division, print_function
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
        instance = self.api.get_instances(
            instance["id"],
            retry_rules=_retry_rules_for_wait(
                max_wait=self.wait, delay=self.update_interval
            ),
        )
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
            instance = self.api.get_instances(
                instance["id"],
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
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
                f"update interval ({update_interval}) is longer than wait ({wait})"
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
                            f" instance {instance['id']}",
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
            self.instance = self.api.get_instances(
                self.instance_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - (time.time() - start_time)),
                    delay=self.update_interval,
                ),
            )
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
        if self.instance["status"] == "RESCUE":
            raise ModuleError("Reboot is not supported in rescue mode.")
        if self.checkmode:
            self.instance["changed"] = True
            return self.instance
        self.api.post_instance_reboot(self.instance_id)
        self.wait_for_statuses(status_done="ACTIVE", statuses_continue=["REBOOTING"])
        self.instance = self.api.get_instances(self.instance_id)
        self.instance["changed"] = True
        return self.instance

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
            self.instance = self.api.get_instances(
                self.instance["id"],
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - (time.time() - start_time)),
                    delay=self.update_interval,
                ),
            )
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
