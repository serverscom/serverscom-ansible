from __future__ import absolute_import, division, print_function
import time

from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    APIError404,
    ScApi,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
    _retry_rules_for_wait,
)


__metaclass__ = type


class ScRBSFlavorsInfo:
    def __init__(self, endpoint, token, location_id):
        self.api = ScApi(token, endpoint)
        self.location_id = location_id

    def run(self):
        return {
            "changed": False,
            "rbs_volume_flavors": list(self.api.list_rbs_flavors(self.location_id)),
        }


class ScRBSVolumeList:
    def __init__(
        self,
        endpoint,
        token,
        label_selector=None,
        search_pattern=None,
        location_id=None,
        location_code=None,
    ):
        self.api = ScApi(token, endpoint)
        self.label_selector = label_selector
        self.search_pattern = search_pattern
        self.location_id = location_id
        self.location_code = location_code

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

    def run(self):
        volumes = list(
            self.api.list_rbs_volumes(
                self.label_selector, self.search_pattern, self.location_id
            )
        )
        for volume in volumes:
            volume_credentials = self.api.get_rbs_volume_credentials(volume["id"])
            volume.update(
                {
                    "username": volume_credentials["username"],
                    "password": volume_credentials["password"],
                }
            )
        return {
            "changed": False,
            "rbs_volumes": volumes,
        }


class scRBSVolumeCreateUpdateDelete:
    def __init__(
        self,
        endpoint,
        token,
        name,
        location_id,
        location_code,
        flavor_id,
        flavor_name,
        size,
        labels,
        volume_id,
        wait,
        update_interval,
        checkmode,
    ):
        self.api = ScApi(token, endpoint)
        self.volume_id = volume_id
        self.name = name
        self.location_id = location_id
        self.location_code = location_code
        self.flavor_id = flavor_id
        self.flavor_name = flavor_name
        self.size = size
        self.labels = labels
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

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

        if not self.flavor_id and self.flavor_name:
            flavors = self.api.list_rbs_flavors(location_id=self.location_id)

            for flavor in flavors:
                if flavor.get("name") == self.flavor_name:
                    self.flavor_id = flavor.get("id")
                    break

            if not self.flavor_id:
                raise ModuleError(
                    f"Flavor with the name '{self.flavor_name}' not found."
                )

    def update_volume(self):
        volume = self.api.get_rbs_volume(self.volume_id)
        result = {"changed": False, "rbs_volume": volume}
        if any(
            [
                self.name and self.name != volume.get("name"),
                self.size and self.size != volume.get("size"),
                self.labels and self.labels != volume.get("labels"),
            ]
        ):
            if not self.checkmode:
                updated_volume = self.api.update_rbs_volume(
                    self.volume_id,
                    name=self.name,
                    size=self.size,
                    labels=self.labels,
                )
                updated_volume = self.wait_for_active()
                result["rbs_volume"] = updated_volume
            else:
                result["rbs_volume"]["name"] = self.name or volume.get("name")
                result["rbs_volume"]["size"] = self.size or volume.get("size")
                result["rbs_volume"]["labels"] = self.labels or volume.get("labels")
            result["changed"] = True
            return result
        else:
            self.wait_for_active()
            result["rbs_volume"]["status"] = "active"
            return result

    def create_or_update_volume(self):
        result = {"changed": False, "rbs_volume": None}
        existing_volume = self.api.get_rbs_volume_by_name(self.name)
        if existing_volume:
            if (
                self.location_id and self.location_id != existing_volume["location_id"]
            ) or (self.flavor_id and self.flavor_id != existing_volume["flavor_id"]):
                raise ModuleError(
                    f"RBS volume with name '{self.name}' already exists. You cannot change its location or flavor."
                )
            else:
                self.volume_id = existing_volume["id"]
                upd = self.update_volume()
                return upd
        else:
            if not (self.location_id and self.flavor_id and self.size):
                raise ModuleError(
                    f"RBS volume with name '{self.name}' does not exist. "
                    "To create it, location_id (or location_code), flavor_id (or flavor_name) and size must be provided."
                )
        if not self.checkmode:
            response = self.api.create_rbs_volume(
                name=self.name,
                location_id=self.location_id,
                flavor_id=self.flavor_id,
                size=self.size,
                labels=self.labels,
            )
            self.volume_id = response.get("id")
            new_volume = self.wait_for_active()
            result["rbs_volume"] = new_volume
        else:
            result["rbs_volume"] = {
                "id": None,
                "name": self.name,
                "location_id": self.location_id,
                "location_code": None,
                "flavor_id": self.flavor_id,
                "size": self.size,
                "labels": self.labels,
                "status": "creating",
            }
        result["changed"] = True
        return result

    def delete_volume(self):
        no_volume = False
        if self.name and not self.volume_id:
            volume = self.api.get_rbs_volume_by_name(self.name)
            if volume:
                self.volume_id = volume["id"]
            else:
                no_volume = True
        try:
            volume = self.api.get_rbs_volume(self.volume_id)
        except APIError404:
            no_volume = True
        if not self.checkmode and not no_volume:
            if volume["status"] != "removing":
                self.api.delete_rbs_volume(self.volume_id)
            self.wait_for_disappearance()
        return {"changed": not no_volume, "rbs_volume": {}}

    def wait_for_active(self):
        volume = self.api.get_rbs_volume(
            self.volume_id,
            retry_rules=_retry_rules_for_wait(
                max_wait=self.wait, delay=self.update_interval
            ),
        )
        if self.wait == 0:
            return volume
        start_time = time.time()
        while True:
            if volume["status"] == "active":
                return volume
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for RBS volume {self.volume_id} to become active after {elapsed:.2f} seconds.",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)
            volume = self.api.get_rbs_volume(
                self.volume_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )

    def wait_for_disappearance(self):
        if self.wait == 0:
            return
        start_time = time.time()
        while True:
            try:
                elapsed = time.time() - start_time
                self.api.get_rbs_volume(
                    self.volume_id,
                    retry_rules=_retry_rules_for_wait(
                        max_wait=max(0, self.wait - elapsed),
                        delay=self.update_interval,
                    ),
                )
            except APIError404:
                return []
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout waiting for RBS volume {self.volume_id} to disappear after {elapsed:.2f} seconds.",
                    timeout=elapsed,
                )
            time.sleep(self.update_interval)


class ScRBSVolumeCredentialsInfo:
    def __init__(self, endpoint, token, volume_id, name):
        self.api = ScApi(token, endpoint)
        self.volume_id = volume_id
        self.name = name

    def run(self):
        if self.name and not self.volume_id:
            existing_volume = self.api.get_rbs_volume_by_name(self.name)
            if existing_volume:
                self.volume_id = existing_volume["id"]
            else:
                raise ModuleError(f"RBS volume with name '{self.name}' not found.")
        rbs_volume_credentials = self.api.get_rbs_volume_credentials(self.volume_id)
        return {
            "changed": False,
            "rbs_volume_credentials": rbs_volume_credentials,
        }


class ScRBSVolumeCredentialsReset:
    def __init__(
        self, endpoint, token, wait, update_interval, checkmode, volume_id, name
    ):
        self.api = ScApi(token, endpoint)
        self.volume_id = volume_id
        self.name = name
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def run(self):
        if self.name and not self.volume_id:
            existing_volume = self.api.get_rbs_volume_by_name(self.name)
            if existing_volume:
                self.volume_id = existing_volume["id"]
            else:
                raise ModuleError(f"RBS volume with name '{self.name}' not found.")
        if not self.checkmode:
            rbs_volume = self.api.reset_rbs_volume_credentials(self.volume_id)
            if self.wait > 0:
                start_time = time.time()
                while True:
                    if rbs_volume["status"] == "active":
                        break
                    elapsed = time.time() - start_time
                    if elapsed > self.wait:
                        raise WaitError(
                            msg=f"Timeout waiting for RBS volume {self.volume_id} to become active after {elapsed:.2f} seconds.",
                            timeout=elapsed,
                        )
                    time.sleep(self.update_interval)
                    rbs_volume = self.api.get_rbs_volume(
                        self.volume_id,
                        retry_rules=_retry_rules_for_wait(
                            max_wait=max(0, self.wait - elapsed),
                            delay=self.update_interval,
                        ),
                    )
                rbs_volume_credentials = self.api.get_rbs_volume_credentials(
                    self.volume_id
                )
                return {
                    "changed": True,
                    "rbs_volume_credentials": rbs_volume_credentials,
                }
        return {
            "changed": True,
            "rbs_volume_credentials": {},
        }
