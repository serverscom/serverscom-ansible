from __future__ import absolute_import, division, print_function
import re
import random
import time

__metaclass__ = type


DEFAULT_API_ENDPOINT = "https://api.servers.com/v1"


class SCBaseError(Exception):
    def __init__(self):
        raise NotImplementedError(
            "This exception should not be called directly. Internal error."
        )

    def fail(self):
        return {"failed": True, "msg": self.msg}


class ToolboxError(SCBaseError):
    def __init__(self, msg):
        self.msg = msg


class APIRequirementsError(SCBaseError):
    def __init__(self, msg):
        self.msg = msg


class APIError(SCBaseError):
    def __init__(self, msg, api_url, status_code):
        self.api_url = api_url
        self.status_code = status_code
        self.msg = msg

    def fail(self):
        return {
            "failed": True,
            "msg": self.msg,
            "api_url": self.api_url,
            "status_code": self.status_code,
        }

    def __repr__(self):
        return f"APIError(msg='{self.msg}', api_url={self.api_url}, status_code={self.status_code})"  # noqa

    def __str__(self):
        return self.__repr__()


class DecodeError(APIError):
    pass


# special classes for well-known (and, may be, expected) HTTP/API errors
class APIError400(APIError):
    pass


class APIError401(APIError):
    pass


class APIError404(APIError):
    pass


class APIError409(APIError):
    pass


class ApiHelper:
    def __init__(self, token, endpoint):
        # pylint: disable=bad-option-value, import-outside-toplevel
        # pylint: disable=bad-option-value, raise-missing-from
        try:
            import requests  # noqa

            self.requests = requests
        except ImportError:
            raise APIRequirementsError(
                msg="The requests library is required (python3-requests)."
            )
        self.session = requests.Session()
        self.request = None
        self.endpoint = endpoint
        self.token = token

    def make_url(self, path):
        return self.endpoint + path

    def start_request(self, method, path, query_parameters):
        """return half-backed request"""
        self.request = self.requests.Request(
            method, self.make_url(path), params=query_parameters
        )

    def send_request(self, good_codes):
        """send a single request/finishes request"""

        self.request.headers["Authorization"] = f"Bearer {self.token}"
        self.request.headers["User-Agent"] = "ansible-module/sc_api/0.1"
        prep_request = self.request.prepare()
        response = self.session.send(prep_request)
        if response.status_code == 400:
            raise APIError400(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg="400 Bad request. Check the object ID.",
            )

        if response.status_code == 401:
            raise APIError401(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg="401 Unauthorized. Check if token is valid.",
            )

        if response.status_code == 404:
            raise APIError404(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg="404 Not Found.",
            )
        if response.status_code == 409:
            raise APIError409(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg=f"409 Conflict. {response.content}",
            )
        if response.status_code not in good_codes:
            raise APIError(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg=f"API Error: {response.content}",
            )
        return response

    def decode(self, response):
        # pylint: disable=bad-option-value, raise-missing-from
        try:
            decoded = response.json()
        except ValueError as e:
            raise DecodeError(
                api_url=response.url,
                status_code=response.status_code,
                msg=f"API decoding error: {str(e)}, data: {response.content}",
            )
        return decoded

    def make_get_request(self, path, query_parameters=None, retry_rules=None):
        """Used for a simple GET request without pagination.

        retry_rules: dict with keys:
            codes: list of status codes to retry on (e.g. [500, 502, 503, 504])
            delay: delay between retries in seconds
            max_wait: maximum total wait time in seconds (+/- additional delay).
        """
        start = time.time()
        while True:
            try:
                self.start_request("GET", path, query_parameters)
                return self.decode(self.send_request(good_codes=[200]))

            except (
                APIError,
                self.requests.exceptions.Timeout,
                self.requests.exceptions.ConnectionError,
            ) as e:
                if not retry_rules:
                    raise
                if (
                    isinstance(e, APIError)
                    and e.status_code not in retry_rules["codes"]
                ):
                    raise
                if time.time() >= start + retry_rules["max_wait"]:
                    raise
                time.sleep(retry_rules["delay"] * random.uniform(0.7, 1.3))

    def make_delete_request(self, path, body, query_parameters, good_codes):
        self.start_request("DELETE", path, query_parameters)
        self.request.body = body
        return self.send_request(good_codes)

    def make_post_request(self, path, body, query_parameters, good_codes):
        self.start_request("POST", path, query_parameters)
        self.request.json = body
        return self.decode(self.send_request(good_codes))

    def make_put_request(self, path, body, query_parameters, good_codes):
        self.start_request("PUT", path, query_parameters)
        self.request.json = body
        response = self.send_request(good_codes)
        return response.status_code, self.decode(response)

    def is_next(self):
        if self.request:
            return bool(self.request.url)
        return False

    def prepare_next(self, response):
        self.request.url = response.links.get("next", {"url": None})["url"]
        self.request.query_params = []

    def make_multipage_request(self, path, query_parameters=None, retry_rules=None):
        """Used for GET request with expected pagination. Returns iterator?"""
        start = time.time()
        transport_errors = (
            self.requests.exceptions.Timeout,
            self.requests.exceptions.ConnectionError,
        )
        self.start_request("GET", path, query_parameters)
        while self.is_next():
            while True:
                try:
                    response = self.send_request(good_codes=[200])
                    break
                except (APIError,) + transport_errors as e:
                    if not retry_rules:
                        raise
                    if (
                        isinstance(e, APIError)
                        and e.status_code not in retry_rules["codes"]
                    ):
                        raise
                    if time.time() >= start + retry_rules["max_wait"]:
                        raise
                    time.sleep(retry_rules["delay"] * random.uniform(0.7, 1.3))
            list_from_api = self.decode(response)
            yield from list_from_api
            self.prepare_next(response)


class ScApiToolbox:
    """Additional functions to work with API."""

    def __init__(self, api):
        self.api = api

    def get_ssh_fingerprints_by_key_name(self, ssh_key_name, must=False):
        """Search for registered ssh key by name and return it's
        fingerprints or return None if nothing found."""
        for key in self.api.list_ssh_keys():
            if key["name"] == ssh_key_name:
                return key["fingerprint"]
        if must:
            raise ToolboxError(f"Unable to find registered ssh key {ssh_key_name}")

    def find_cloud_image_id_by_name_regexp(self, regexp, region_id=None, must=False):
        for image in self.api.list_images(region_id):
            if re.match(regexp, image["name"]):
                return image["id"]
        if must:
            raise ToolboxError(f"Unable to find image by regexp {regexp}")

    def find_image_id(self, image_id, image_regexp, region_id=None, must=False):
        if image_id and image_regexp:
            raise ToolboxError("Both image_id and image_regexp specified.")
        if image_id:
            return image_id
        if image_regexp:
            return self.find_cloud_image_id_by_name_regexp(
                image_regexp, region_id, must=must
            )
        raise ToolboxError("No image_id and no image_regexp specified.")

    def find_cloud_flavor_id_by_name(self, flavor_name, region_id=None, must=False):
        """Search flavor by exact name match.

        Returns flavor_id if found, or None if not found."""
        for flavor in self.api.list_flavors(region_id):
            if flavor["name"] == flavor_name:
                return flavor["id"]
        if must:
            raise ToolboxError(f"Unable to find flavor by name {flavor_name}")

    def find_cloud_instance_id_by_name(self, name, region_id=None, must=False):
        instances = self.api.list_instances(region_id)
        found = []
        for instance in instances:
            if instance["name"] == name:
                found.append(instance)
        if len(found) > 1:
            raise ToolboxError(f"Multiple instances found with name {name}")
        if len(found) == 1:
            return found[0]
        if must:
            raise ToolboxError(f"Unable to find instance by name {name}")

    def find_instance(self, instance_id, instance_name, region_id=None, must=False):
        """Search instance either by id, or by name (and region).

        Returns instance object, raises an exception if nothing
        found (and must=True), or return None (if must=False).
        Raises an exception if multiple instances found with the
        same name.
        """
        if instance_id and instance_name:
            raise ToolboxError("Both instance_id and instance_name are specified.")
        if not instance_id and not instance_name:
            raise ToolboxError("Neither instance_id nor instance_name specified.")
        if instance_id:
            try:
                return self.api.get_instances(instance_id)
            except APIError404:
                if must:
                    raise
                return None
        if instance_name:
            return self.find_cloud_instance_id_by_name(instance_name, must=must)

    def find_flavor_id(self, flavor_id, flavor_name, region_id=None):
        """Search for flavor by id or by name.

        Returns flavor id, by id or by name.
        Raises an exception if nothing found.
        """
        if flavor_id and flavor_name:
            raise ToolboxError("Both flavor_id and flavor_name specified.")

        if not flavor_id and not flavor_name:
            raise ToolboxError("Neither flavor_id nor flavor_name specified.")
        if flavor_id:
            return flavor_id
        return self.find_cloud_flavor_id_by_name(
            flavor_name=flavor_name, region_id=region_id, must=True
        )


# naiming convention:
# Prefixes:
# list_ -> returns interator over paginatated response.
# get_ -> returns single object
# post_ -> make post request for a single object (update/create/change)
# delete_ -> make delete request for a single object
# Suffixes:
# Last element of the path (except for the path parameter)
# if there is no collision, more path pieces if there are collisions.
# Arguments:
# 'as is' in the API if possible.


class ScApi:
    """Provide functions matching Servers.com Public API."""

    def __init__(self, token, endpoint=DEFAULT_API_ENDPOINT):
        self.api_helper = ApiHelper(token, endpoint)
        self.toolbox = ScApiToolbox(self)

    def list_locations(self, search_pattern=None):
        if search_pattern:
            query = {"search_pattern": search_pattern}
        else:
            query = None
        return self.api_helper.make_multipage_request(
            path="/locations", query_parameters=query
        )

    def list_regions(self):
        return self.api_helper.make_multipage_request("/cloud_computing/regions")

    def get_dedicated_servers(self, server_id, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/hosts/dedicated_servers/{server_id}",
            retry_rules=retry_rules,
        )

    def get_sbm_servers(self, server_id, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/hosts/sbm_servers/{server_id}",
            retry_rules=retry_rules,
        )

    def post_sbm_server_power_on(self, server_id):
        return self.api_helper.make_post_request(
            path=f"/hosts/sbm_servers/{server_id}/power_on",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_sbm_server_power_off(self, server_id):
        return self.api_helper.make_post_request(
            path=f"/hosts/sbm_servers/{server_id}/power_off",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_sbm_server_power_cycle(self, server_id):
        return self.api_helper.make_post_request(
            path=f"/hosts/sbm_servers/{server_id}/power_cycle",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_sbm_server_reinstall(
        self,
        server_id,
        hostname,
        operating_system_id,
        ssh_key_fingerprints=None,
        user_data=None,
    ):
        body = {
            "hostname": hostname,
            "operating_system_id": operating_system_id,
        }
        if ssh_key_fingerprints is not None:
            body["ssh_key_fingerprints"] = ssh_key_fingerprints
        if user_data is not None:
            body["user_data"] = user_data
        return self.api_helper.make_post_request(
            path=f"/hosts/sbm_servers/{server_id}/reinstall",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def list_sbm_server_ptr_records(self, server_id):
        return self.api_helper.make_multipage_request(
            path=f"/hosts/sbm_servers/{server_id}/ptr_records"
        )

    def post_sbm_server_ptr_record(
        self, server_id, ip, domain, ttl=None, priority=None
    ):
        body = {"ip": ip, "domain": domain}
        if ttl is not None:
            body["ttl"] = ttl
        if priority is not None:
            body["priority"] = priority
        return self.api_helper.make_post_request(
            path=f"/hosts/sbm_servers/{server_id}/ptr_records",
            body=body,
            query_parameters=None,
            good_codes=[201],
        )

    def delete_sbm_server_ptr_record(self, server_id, record_id):
        return self.api_helper.make_delete_request(
            path=f"/hosts/sbm_servers/{server_id}/ptr_records/{record_id}",
            body=None,
            query_parameters=None,
            good_codes=[204],
        )

    def post_sbm_servers(
        self,
        location_id,
        sbm_flavor_model_id,
        hosts,
        operating_system_id,
        ssh_key_fingerprints=None,
        user_data=None,
    ):
        body = {
            "location_id": location_id,
            "sbm_flavor_model_id": sbm_flavor_model_id,
            "hosts": hosts,
            "operating_system_id": operating_system_id,
        }
        if ssh_key_fingerprints is not None:
            body["ssh_key_fingerprints"] = ssh_key_fingerprints
        if user_data is not None:
            body["user_data"] = user_data
        return self.api_helper.make_post_request(
            path="/hosts/sbm_servers",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def delete_sbm_server(self, server_id):
        return self.api_helper.make_delete_request(
            path=f"/hosts/sbm_servers/{server_id}",
            body=None,
            query_parameters=None,
            good_codes=[200],
        )

    def list_sbm_servers(
        self,
        search_pattern=None,
        location_id=None,
        rack_id=None,
        label_selector=None,
    ):
        query = {}
        if search_pattern:
            query["search_pattern"] = search_pattern
        if location_id is not None:
            query["location_id"] = location_id
        if rack_id:
            query["rack_id"] = rack_id
        if label_selector:
            query["label_selector"] = label_selector
        return self.api_helper.make_multipage_request(
            path="/hosts/sbm_servers", query_parameters=query
        )

    def put_sbm_server(self, server_id, labels):
        body = {"labels": labels}
        return self.api_helper.make_put_request(
            path=f"/hosts/sbm_servers/{server_id}",
            body=body,
            query_parameters=None,
            good_codes=[200],
        )

    def list_sbm_server_networks(
        self,
        server_id,
        search_pattern=None,
        family=None,
        interface_type=None,
        distribution_method=None,
        additional=None,
    ):
        query = {}
        if search_pattern:
            query["search_pattern"] = search_pattern
        if family:
            query["family"] = family
        if interface_type:
            query["interface_type"] = interface_type
        if distribution_method:
            query["distribution_method"] = distribution_method
        if additional is not None:
            query["additional"] = additional
        return self.api_helper.make_multipage_request(
            path=f"/hosts/sbm_servers/{server_id}/networks",
            query_parameters=query,
        )

    def get_sbm_server_network(self, server_id, network_id, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/hosts/sbm_servers/{server_id}/networks/{network_id}",
            retry_rules=retry_rules,
        )

    def delete_sbm_server_network(self, server_id, network_id):
        return self.api_helper.make_delete_request(
            path=f"/hosts/sbm_servers/{server_id}/networks/{network_id}",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_sbm_server_private_ipv4_network(
        self, server_id, mask, distribution_method=None
    ):
        body = {"mask": mask}
        if distribution_method:
            body["distribution_method"] = distribution_method
        return self.api_helper.make_post_request(
            path=f"/hosts/sbm_servers/{server_id}/networks/private_ipv4",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def list_hosts(self, type=None, search_pattern=None, label_selector=None):
        query = {}
        if type:
            query["type"] = type
        if search_pattern:
            query["search_pattern"] = search_pattern
        if label_selector:
            query["label_selector"] = label_selector

        return self.api_helper.make_multipage_request(
            path="/hosts", query_parameters=query
        )

    def post_dedicated_server_reinstall(
        self,
        server_id,
        hostname,
        operating_system_id,
        ssh_key_fingerprints,
        drives,
        user_data,
    ):
        body = {
            "hostname": hostname,
            "operating_system_id": operating_system_id,
            "ssh_key_fingerprints": ssh_key_fingerprints,
            "drives": drives,
        }
        if user_data:
            body["user_data"] = user_data
        return self.api_helper.make_post_request(
            path=f"/hosts/dedicated_servers/{server_id}/reinstall",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def list_ssh_keys(self, label_selector=None):
        query = {}
        if label_selector:
            query["label_selector"] = label_selector
        return self.api_helper.make_multipage_request(
            "/ssh_keys", query_parameters=query
        )

    def post_ssh_keys(self, name, public_key, labels=None):
        body = {
            "name": name,
            "public_key": public_key,
        }
        if labels:
            body["labels"] = labels
        return self.api_helper.make_post_request(
            path="/ssh_keys",
            body=body,
            query_parameters=None,
            # query_parameters={"name": name, "public_key": public_key},
            good_codes=[201],
        )

    def delete_ssh_keys(self, fingerprint):
        return self.api_helper.make_delete_request(
            path=f"/ssh_keys/{fingerprint}",
            body=None,
            query_parameters=None,
            good_codes=[204],
        )

    def get_instances(self, instance_id, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/cloud_computing/instances/{instance_id}",
            retry_rules=retry_rules,
        )

    def get_credentials(self, region_id):
        return self.api_helper.make_get_request(
            path=f"/cloud_computing/regions/{region_id}/credentials"
        )

    def list_flavors(self, region_id):
        return self.api_helper.make_multipage_request(
            path=f"/cloud_computing/regions/{region_id}/flavors"
        )

    def list_images(self, region_id):
        return self.api_helper.make_multipage_request(
            path=f"/cloud_computing/regions/{region_id}/images"
        )

    def list_instances(self, region_id=None, label_selector=None):
        query = {}
        if region_id:
            query["region_id"] = region_id
        if label_selector:
            query["label_selector"] = label_selector

        return self.api_helper.make_multipage_request(
            path="/cloud_computing/instances", query_parameters=query
        )

    def post_instances_reinstall(self, instance_id, image_id):
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/reinstall",
            body=None,
            query_parameters={"image_id": image_id},
            good_codes=[202],
        )

    def post_instance(
        self,
        region_id,
        name,
        flavor_id,
        image_id,
        gpn_enabled,
        ipv6_enabled,
        ipv4_enabled,
        ssh_key_fingerprint,
        backup_copies,
        user_data,
        labels,
    ):
        body = {
            "region_id": region_id,
            "name": name,
            "flavor_id": flavor_id,
            "image_id": image_id,
        }
        if gpn_enabled:
            body["gpn_enabled"] = True
        if not ipv4_enabled:
            body["ipv4_enabled"] = False
        if ipv6_enabled:
            body["ipv6_enabled"] = True
        if ssh_key_fingerprint:
            body["ssh_key_fingerprint"] = ssh_key_fingerprint
        if backup_copies is not None:
            body["backup_copies"] = backup_copies
        if user_data:
            body["user_data"] = user_data
        if labels:
            body["labels"] = labels
        return self.api_helper.make_post_request(
            path="/cloud_computing/instances",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def delete_instance(self, instance_id):
        return self.api_helper.make_delete_request(
            path=f"/cloud_computing/instances/{instance_id}",
            query_parameters=None,
            body=None,
            good_codes=[202],
        )

    def list_instance_ptr_records(self, instance_id):
        return self.api_helper.make_multipage_request(
            path=f"/cloud_computing/instances/{instance_id}/ptr_records"
        )

    def delete_instance_ptr_records(self, instance_id, record_id):
        return self.api_helper.make_delete_request(
            path=f"/cloud_computing/instances/{instance_id}/ptr_records/{record_id}",  # noqa
            body=None,
            query_parameters=None,
            good_codes=[204],
        )

    def post_instance_ptr_records(self, instance_id, data, ip, ttl=None, priority=None):
        query_parameters = {
            "data": data,
            "ip": ip,
        }
        if ttl is not None:
            query_parameters["ttl"] = ttl
        if priority is not None:
            query_parameters["priority"] = priority
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/ptr_records",
            query_parameters=query_parameters,
            body=None,
            good_codes=[201],
        )

    def post_instance_switch_on(self, instance_id):
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/switch_on",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_instance_switch_off(self, instance_id):
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/switch_off",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_instance_rescue(self, instance_id, image_id=None):
        if image_id:
            body = {"image_id": image_id}
        else:
            body = None
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/rescue",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def post_instance_unrescue(self, instance_id):
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/unrescue",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_instance_reboot(self, instance_id):
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/reboot",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_instances_approve_upgrade(self, instance_id):
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/approve_upgrade",
            body=None,
            query_parameters=None,
            good_codes=[201],
        )

    def post_instances_revert_upgrade(self, instance_id):
        return self.api_helper.make_post_request(
            path=f"/cloud_computing/instances/{instance_id}/revert_upgrade",
            body=None,
            query_parameters=None,
            good_codes=[201],
        )

    def list_l2_segments(self, label_selector=None):
        query = {}
        if label_selector:
            query["label_selector"] = label_selector
        return self.api_helper.make_multipage_request(
            path="/l2_segments", query_parameters=query
        )

    def list_l2_location_groups(self):
        return self.api_helper.make_multipage_request(
            path="/l2_segments/location_groups"
        )

    def list_l2_segment_members(self, l2_segment_id):
        return self.api_helper.make_multipage_request(
            path=f"/l2_segments/{l2_segment_id}/members"
        )

    def list_l2_segment_networks(self, l2_segment_id):
        return self.api_helper.make_multipage_request(
            path=f"/l2_segments/{l2_segment_id}/networks"
        )

    def put_l2_segment_networks(self, l2_segment_id, create, delete):
        '''create: object: mask (int), distribution_method: must be "route"'''
        body = {"create": create, "delete": delete}
        response = self.api_helper.make_put_request(
            path=f"/l2_segments/{l2_segment_id}/networks",
            query_parameters=None,
            body=body,
            good_codes=[200, 202],
        )[1]
        return response

    def get_l2_segment(self, l2_segment_id, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/l2_segments/{l2_segment_id}",
            retry_rules=retry_rules,
        )

    def get_l2_segment_or_none(self, l2_segment_id, retry_rules=None):
        try:
            seg = self.api_helper.make_get_request(
                path=f"/l2_segments/{l2_segment_id}",
                retry_rules=retry_rules,
            )
        except APIError404:
            seg = {"id": None}
        return seg

    def delete_l2_segment(self, l2_segment_id):
        return self.api_helper.make_delete_request(
            path=f"/l2_segments/{l2_segment_id}",
            query_parameters=None,
            body=None,
            good_codes=[202, 204],
        )

    def post_l2_segment(self, name, type, location_group_id, members, labels=None):
        body = {
            "name": name,
            "members": members,
            "type": type,
            "location_group_id": location_group_id,
        }
        if labels:
            body["labels"] = labels

        return self.api_helper.make_post_request(
            path="/l2_segments/",
            body=body,
            query_parameters=None,
            good_codes=[200, 202],
        )

    def put_l2_segment_update(self, l2_segment_id, members, labels=None):
        body = {"members": members}
        if labels:
            body["labels"] = labels

        response = self.api_helper.make_put_request(
            path=f"/l2_segments/{l2_segment_id}",
            body=body,
            query_parameters=None,
            good_codes=[200, 202],
        )[1]
        return response

    def list_load_balancer_instances(self, label_selector=None, retry_rules=None):
        query = {}
        if label_selector:
            query["label_selector"] = label_selector
        return self.api_helper.make_multipage_request(
            path="/load_balancers",
            query_parameters=query,
            retry_rules=retry_rules,
        )

    def get_lb_instance(self, instance_id, lb_instance_type, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/load_balancers/{lb_instance_type}/{instance_id}",
            retry_rules=retry_rules,
        )

    def delete_lb_instance(self, instance_id, lb_instance_type):
        return self.api_helper.make_delete_request(
            path=f"/load_balancers/{lb_instance_type}/{instance_id}",
            query_parameters=None,
            body=None,
            good_codes=[204],
        )

    def lb_instance_l4_create(
        self,
        name,
        location_id,
        cluster_id,
        store_logs,
        store_logs_region_id,
        vhost_zones,
        upstream_zones,
        labels,
    ):
        body = {
            "name": name,
            "location_id": location_id,
            "vhost_zones": vhost_zones,
            "upstream_zones": upstream_zones,
        }
        if cluster_id is not None:
            body["cluster_id"] = cluster_id
        if store_logs:
            body["store_logs"] = True
        if store_logs_region_id is not None:
            body["store_logs_region_id"] = store_logs_region_id
        if labels:
            body["labels"] = labels

        return self.api_helper.make_post_request(
            path="/load_balancers/l4",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def lb_instance_l4_update(
        self,
        lb_id,
        name,
        store_logs,
        store_logs_region_id,
        new_external_ips_count,
        delete_external_ips,
        cluster_id,
        shared_cluster,
        vhost_zones,
        upstream_zones,
        labels,
    ):
        body = {}
        if name is not None:
            body["name"] = name
        if store_logs is not None:
            body["store_logs"] = store_logs
        if store_logs_region_id is not None:
            body["store_logs_region_id"] = store_logs_region_id
        if new_external_ips_count is not None:
            body["new_external_ips_count"] = new_external_ips_count
        if delete_external_ips is not None:
            body["delete_external_ips"] = delete_external_ips
        if cluster_id is not None:
            body["cluster_id"] = cluster_id
        if shared_cluster is not None:
            body["shared_cluster"] = shared_cluster
        if vhost_zones is not None:
            body["vhost_zones"] = vhost_zones
        if upstream_zones is not None:
            body["upstream_zones"] = upstream_zones
        if labels is not None:
            body["labels"] = labels

        return self.api_helper.make_put_request(
            path=f"/load_balancers/l4/{lb_id}",
            body=body,
            query_parameters=None,
            good_codes=[200, 202],
        )

    def lb_instance_l7_create(
        self,
        name,
        location_id,
        cluster_id,
        store_logs,
        store_logs_region_id,
        geoip,
        vhost_zones,
        upstream_zones,
        labels,
    ):
        body = {
            "name": name,
            "location_id": location_id,
            "vhost_zones": vhost_zones,
            "upstream_zones": upstream_zones,
        }
        if cluster_id is not None:
            body["cluster_id"] = cluster_id
        if store_logs:
            body["store_logs"] = True
        if store_logs_region_id is not None:
            body["store_logs_region_id"] = store_logs_region_id
        if geoip is not None:
            body["geoip"] = geoip
        if labels:
            body["labels"] = labels

        return self.api_helper.make_post_request(
            path="/load_balancers/l7",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def lb_instance_l7_update(
        self,
        lb_id,
        name,
        store_logs,
        store_logs_region_id,
        geoip,
        new_external_ips_count,
        delete_external_ips,
        cluster_id,
        shared_cluster,
        vhost_zones,
        upstream_zones,
        labels,
    ):
        body = {}
        if name is not None:
            body["name"] = name
        if store_logs is not None:
            body["store_logs"] = store_logs
        if store_logs_region_id is not None:
            body["store_logs_region_id"] = store_logs_region_id
        if geoip is not None:
            body["geoip"] = geoip
        if new_external_ips_count is not None:
            body["new_external_ips_count"] = new_external_ips_count
        if delete_external_ips is not None:
            body["delete_external_ips"] = delete_external_ips
        if cluster_id is not None:
            body["cluster_id"] = cluster_id
        if shared_cluster is not None:
            body["shared_cluster"] = shared_cluster
        if vhost_zones is not None:
            body["vhost_zones"] = vhost_zones
        if upstream_zones is not None:
            body["upstream_zones"] = upstream_zones
        if labels is not None:
            body["labels"] = labels

        return self.api_helper.make_put_request(
            path=f"/load_balancers/l7/{lb_id}",
            body=body,
            query_parameters=None,
            good_codes=[200, 202],
        )

    def post_dedicated_server_power_on(self, server_id):
        return self.api_helper.make_post_request(
            path=f"/hosts/dedicated_servers/{server_id}/power_on",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def post_dedicated_server_power_off(self, server_id):
        return self.api_helper.make_post_request(
            path=f"/hosts/dedicated_servers/{server_id}/power_off",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )

    def list_server_models(self, location_id, search_pattern=None):
        if search_pattern:
            query = {"search_pattern": search_pattern}
        else:
            query = None
        return self.api_helper.make_multipage_request(
            path=f"/locations/{location_id}/order_options/server_models",
            query_parameters=query,
        )

    def list_sbm_flavor_models(self, location_id, search_pattern=None):
        if search_pattern:
            query = {"search_pattern": search_pattern}
        else:
            query = None
        return self.api_helper.make_multipage_request(
            path=f"/locations/{location_id}/order_options/sbm_flavor_models",
            query_parameters=query,
        )

    def list_os_images_by_model_id(self, location_id, model_id):
        return self.api_helper.make_multipage_request(
            path=f"/locations/{location_id}/order_options/server_models/{model_id}/operating_systems",
            query_parameters=None,
        )

    def list_os_images_by_sbm_flavor_id(self, location_id, sbm_flavor_id):
        return self.api_helper.make_multipage_request(
            path=f"/locations/{location_id}/order_options/sbm_flavor_models/{sbm_flavor_id}/operating_systems",
            query_parameters=None,
        )

    def list_rbs_flavors(self, location_id):
        return self.api_helper.make_multipage_request(
            path=f"/locations/{location_id}/order_options/remote_block_storage/flavors",
            query_parameters=None,
        )

    def list_rbs_volumes(
        self, label_selector=None, search_pattern=None, location_id=None
    ):
        query = None
        if any([label_selector, search_pattern, location_id]):
            query = {}
            if label_selector:
                query["label_selector"] = label_selector
            if search_pattern:
                query["search_pattern"] = search_pattern
            if location_id:
                query["location_id"] = location_id

        return self.api_helper.make_multipage_request(
            path="/remote_block_storage/volumes", query_parameters=query
        )

    def get_rbs_volume(self, rbs_volume_id, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/remote_block_storage/volumes/{rbs_volume_id}",
            retry_rules=retry_rules,
        )

    def get_rbs_volume_by_name(self, name):
        try:
            candidates = self.list_rbs_volumes(search_pattern=name)
            for candidate in candidates:
                if candidate["name"] == name:
                    return candidate
        except APIError404:
            return None
        return None

    def create_rbs_volume(self, name, flavor_id, size, location_id, labels=None):
        body = {
            "name": name,
            "flavor_id": flavor_id,
            "size": size,
            "location_id": location_id,
        }
        if labels:
            body["labels"] = labels
        return self.api_helper.make_post_request(
            path="/remote_block_storage/volumes",
            body=body,
            query_parameters=None,
            good_codes=[202],
        )

    def update_rbs_volume(self, rbs_volume_id, name=None, size=None, labels=None):
        body = None
        if any([name, size, labels]):
            body = {}
            if name is not None:
                body["name"] = name
            if size is not None:
                body["size"] = size
            if labels is not None:
                body["labels"] = labels

        return self.api_helper.make_put_request(
            path=f"/remote_block_storage/volumes/{rbs_volume_id}",
            body=body,
            query_parameters=None,
            good_codes=[200, 202],
        )

    def delete_rbs_volume(self, rbs_volume_id):
        return self.api_helper.make_delete_request(
            path=f"/remote_block_storage/volumes/{rbs_volume_id}",
            body=None,
            query_parameters=None,
            good_codes=[204],
        )

    def get_rbs_volume_credentials(self, rbs_volume_id, retry_rules=None):
        return self.api_helper.make_get_request(
            path=f"/remote_block_storage/volumes/{rbs_volume_id}/credentials",
            retry_rules=retry_rules,
        )

    def reset_rbs_volume_credentials(self, rbs_volume_id):
        return self.api_helper.make_post_request(
            path=f"/remote_block_storage/volumes/{rbs_volume_id}/reset_credentials",
            body=None,
            query_parameters=None,
            good_codes=[202],
        )
