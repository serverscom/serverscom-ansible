from __future__ import absolute_import, division, print_function
import time

from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    ScApi,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    WaitError,
    _retry_rules_for_wait,
)


__metaclass__ = type


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
            segment = self.api.get_l2_segment(
                segment_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
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
            segment = self.api.get_l2_segment_or_none(
                segment_id,
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )
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
            l2 = self.api.get_l2_segment(
                l2["id"],
                retry_rules=_retry_rules_for_wait(
                    max_wait=max(0, self.wait - elapsed),
                    delay=self.update_interval,
                ),
            )

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
