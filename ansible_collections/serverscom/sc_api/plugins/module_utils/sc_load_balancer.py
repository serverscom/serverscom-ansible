from __future__ import absolute_import, division, print_function
import time

from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    APIError400,
    APIError404,
    ScApi,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
    _retry_rules_for_wait,
)


__metaclass__ = type


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
                    msg=f"There are more than one instance with the specified name: {instance_ids}. Such configuration is not supported by the module."
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
            elapsed = time.time() - start_time
            instances = self.api.list_load_balancer_instances(
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                )
            )
            exists = any(
                inst.get("id") == self.lb_instance_id
                for inst in instances
                if inst.get("type") == self.lb_instance_type
            )
            if not exists:
                break
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
            shared_cluster=self.shared_cluster,
            vhost_zones=self.vhost_zones,
            upstream_zones=self.upstream_zones,
            labels=self.labels,
        )

    def wait_for_active(self):
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            instance = self.api.get_lb_instance(
                self.lb_instance_id,
                self.lb_instance_type,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
            if instance["status"] == "active":
                return instance
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
            shared_cluster=self.shared_cluster,
            geoip=self.geoip,
            vhost_zones=self.vhost_zones,
            upstream_zones=self.upstream_zones,
            labels=self.labels,
        )

    def wait_for_active(self):
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            instance = self.api.get_lb_instance(
                self.lb_instance_id,
                self.lb_instance_type,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
            if instance["status"] == "active":
                return instance
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
