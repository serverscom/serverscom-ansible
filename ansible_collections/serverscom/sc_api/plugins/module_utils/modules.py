from __future__ import (absolute_import, division, print_function)
import hashlib
from textwrap import wrap
import base64
import time
from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    SCBaseError,
    APIError404,
    APIError409,
    DEFAULT_API_ENDPOINT,
    ScApi
)

__metaclass__ = type


CHANGED = True
NOT_CHANGED = False


class ModuleError(SCBaseError):
    def __init__(self, msg):
        self.msg = msg

    def fail(self):
        return {
            'failed': True,
            'msg': self.msg
        }


class WaitError(ModuleError):
    def __init__(self, msg, timeout):
        self.msg = msg
        self.timeout = timeout

    def fail(self):
        return {
            'failed': True,
            'timeout': self.timeout,
            'msg': self.msg
        }


class ScDedicatedServerInfo(object):
    def __init__(self, endpoint, token, name, fail_on_absent):
        self.api = ScApi(token, endpoint)
        self.server_id = name
        self.fail_on_absent = fail_on_absent

    @staticmethod
    def _is_server_ready(server_info):
        if (
            server_info.get('status') == 'active' and
            server_info.get('power_status') == 'powered_on' and
            server_info.get('operational_status') == 'normal'
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
            return {
                'changed': False,
                'found': False,
                'ready': False
            }
        module_output = server_info
        module_output['found'] = True
        module_output['ready'] = self._is_server_ready(server_info)
        module_output['changed'] = False
        return module_output


class ScBaremetalServersInfo():
    def __init__(self, endpoint, token):
        self.api = ScApi(token, endpoint)

    def run(self):
        return {
            'changed': False,
            'baremetal_servers': list(self.api.list_hosts())
        }


class ScBaremetalLocationsInfo(object):
    def __init__(self, endpoint, token,
                 search_pattern, required_features):
        self.search_pattern = search_pattern
        self.required_features = required_features
        self.api = ScApi(token, endpoint)

    @staticmethod
    def location_features(location):
        features = set(location['supported_features'])
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
        ret_data = {'changed': False}
        ret_data["locations"] = self.locations()
        return ret_data


class ScCloudComputingRegionsInfo(object):
    def __init__(self, endpoint, token,
                 search_pattern):
        self.search_pattern = search_pattern
        self.api = ScApi(token, endpoint)

    @staticmethod
    def location_features(location):
        features = set(location['supported_features'])
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
                if self.search_pattern.lower() in region['name'].lower() or \
                   self.search_pattern.lower() in region['code'].lower():
                    yield region

    def run(self):
        ret_data = {'changed': False}
        ret_data['regions'] = list(
            self.search(self.regions())
        )
        return ret_data


class ScSshKey(object):
    def __init__(
        self, endpoint, token, state, name, fingerprint,
        public_key, replace, checkmode
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
        if public_key:
            self.fingerprint = self.extract_fingerprint(public_key)
            if fingerprint and self.fingerprint != fingerprint:
                raise ModuleError(
                    msg='Fingerprint does not match public_key'
                )
        if state == 'absent':
            if not any([fingerprint, name, public_key]):
                raise ModuleError(
                    'Need at least one of name, fingerprint, public_key '
                    'for state=absent'
                )
        if state == 'present':
            if not public_key:
                raise ModuleError(
                    'Need public_key for state=present'
                )
            if not name:
                raise ModuleError(
                    'Need name for state=present'
                )

    @staticmethod
    def extract_fingerprint(public_key):
        parts = public_key.split()
        # real key is the largest word in the line
        parts.sort(key=len, reverse=True)
        the_key = base64.decodebytes(parts[0].encode('ascii'))
        digest = hashlib.md5(the_key).hexdigest()
        fingerprint = ':'.join(wrap(digest, 2))
        return fingerprint

    @staticmethod
    def classify_matching_keys(key_list, name, fingerprint):
        full_match = []
        partial_match = []
        any_match = []
        for key in key_list:
            if key['name'] == name or key['fingerprint'] == fingerprint:
                any_match.append(key)
                if key['name'] == name and key['fingerprint'] == fingerprint:
                    full_match.append(key)
                else:
                    partial_match.append(key)
        return (full_match, partial_match, any_match)

    def add_key(self):
        if not self.checkmode:
            return self.api.post_ssh_keys(
                name=self.key_name, public_key=self.public_key
            )

    def delete_keys(self, key_list):
        if not self.checkmode:
            for key in key_list:
                self.api.delete_ssh_keys(fingerprint=key['fingerprint'])

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
                'Error: Partial match found and no replace option. '
                f'Partially matching keys: {repr(self.partial_match)}'
            )
        if self.partial_match and self.replace:
            self.delete_keys(self.partial_match)
            changed = CHANGED
        if not self.full_match:
            self.add_key()
            changed = CHANGED
        return changed

    def run(self):
        self.full_match, self.partial_match, self.any_match = \
            self.classify_matching_keys(
                self.api.list_ssh_keys(), self.key_name, self.fingerprint
            )
        if self.state == 'absent':
            changed = self.state_absent()
        if self.state == 'present':
            changed = self.state_present()
        return {'changed': changed}


class ScSshKeysInfo():
    def __init__(self, endpoint, token):
        self.api = ScApi(token, endpoint)

    def run(self):
        return {
            'changed': False,
            'ssh_keys': list(self.api.list_ssh_keys())
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
        checkmode
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
        self.drives_layout = self.get_drives_layout(drives_layout,
                                                    drives_layout_template)
        self.operating_system_id = self.get_operating_system_id(
            operating_system_id
        )
        self.ssh_keys = self.get_ssh_keys(ssh_keys, ssh_key_name)
        self.wait = wait
        self.update_interval = update_interval
        self.user_data = user_data
        self.checkmode = checkmode

    def get_server_data(self):
        if not self.old_server_data:
            self.old_server_data = \
                self.api.get_dedicated_servers(self.server_id)

    def get_hostname(self, hostname):
        if hostname:
            return hostname
        self.get_server_data()
        if 'title' not in self.old_server_data:
            raise ModuleError(
                "Unable to retrive old title for the server. "
                "use hostname option to specify the hostname for reinstall."
            )
        return self.old_server_data['title']

    def get_operating_system_id(self, operating_system_id):
        if operating_system_id:
            return operating_system_id
        self.get_server_data()
        cfg = self.old_server_data.get('configuration_details')
        if not cfg or 'operating_system_id' not in cfg:
            raise ModuleError(
                "no operating_system_id was given, and unable to get old"
                "operating_system_id"
            )
        return cfg['operating_system_id']

    def get_ssh_keys(self, ssh_keys, ssh_key_name):
        if ssh_keys:
            return ssh_keys
        if not ssh_key_name:
            return []
        return [self.api.toolbox.get_ssh_fingerprints_by_key_name(
            ssh_key_name, must=True)]

    @staticmethod
    def get_drives_layout(layout, template):
        partitions_template = [
            {
                "target": "/boot",
                "size": 1024,
                "fill": False, "fs": "ext4"
            },
            {
                "target": "swap",
                "size": 4096,
                "fill": False
            },
            {
                "target": "/",
                "fill": True,
                "fs": "ext4"
            }
        ]
        rai1_simple = [{
            'slot_positions': [0, 1],
            'raid': 1,
            'partitions': partitions_template
        }]
        raid0_simple = [{
            'slot_positions': [0],
            'raid': 0,
            'partitions': partitions_template
        }]
        templates = {
            'raid1-simple': rai1_simple,
            'raid0-simple': raid0_simple
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
                raise WaitError(
                    msg="Server is not ready.",
                    timeout=elapsed
                )
            server_info = self.api.get_dedicated_servers(self.server_id)
            ready = ScDedicatedServerInfo._is_server_ready(server_info)
        server_info['ready'] = True
        server_info['elapsed'] = elapsed
        return server_info

    def run(self):
        if self.checkmode:
            return {'changed': True}
        result = self.api.post_dedicated_server_reinstall(
            server_id=self.server_id,
            hostname=self.hostname,
            operating_system_id=self.operating_system_id,
            ssh_key_fingerprints=self.ssh_keys,
            user_data=self.user_data,
            drives={
                'layout': self.drives_layout,
            }
        )
        if self.wait:
            result = self.wait_for_server()
        result['changed'] = True
        return result


class ScCloudComputingFlavorsInfo():
    def __init__(self, endpoint, token, region_id):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id

    def run(self):
        return {
            'changed': False,
            'cloud_flavors': list(self.api.list_flavors(self.region_id))
        }


class ScCloudComputingImagesInfo():
    def __init__(self, endpoint, token, region_id):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id

    def run(self):
        return {
            'changed': False,
            'cloud_images': list(self.api.list_images(self.region_id))
        }


class ScCloudComputingInstancesInfo():
    def __init__(self, endpoint, token, region_id):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id

    def run(self):
        return {
            'changed': False,
            'cloud_instances': list(self.api.list_instances(self.region_id))
        }


class ScCloudComputingInstanceInfo():
    def __init__(self, endpoint, token, instance_id, name, region_id):
        self.api = ScApi(token, endpoint)
        self.instance_id = self.api.toolbox.find_instance(
            instance_id=instance_id,
            instance_name=name,
            region_id=region_id,
            must=True
        )['id']

    def run(self):
        result = self.api.get_instances(self.instance_id)
        result['changed'] = False
        return result


class ScCloudComputingOpenstackCredentials():

    def __init__(self, endpoint, token, region_id):
        self.api = ScApi(token, endpoint)
        self.region_id = region_id

    def run(self):
        result = self.api.get_credentials(self.region_id)
        result['changed'] = False
        return result


class ScCloudComputingInstanceCreate():
    def __init__(
        self,
        endpoint, token,
        region_id, name,
        image_id, image_regexp,
        flavor_id, flavor_name,
        gpn_enabled, ipv6_enabled,
        ssh_key_fingerprint, ssh_key_name,
        backup_copies,
        wait, update_interval,
        checkmode
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
            image_id=image_id,
            image_regexp=image_regexp,
            region_id=region_id,
            must=True
        )
        self.gpn_enabled = gpn_enabled
        self.ipv6_enabled = ipv6_enabled
        self.ssh_key_fingerprint = self.get_ssh_key_fingerprint(
            ssh_key_fingerprint,
            ssh_key_name
        )
        self.backup_copies = backup_copies
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def get_ssh_key_fingerprint(self, ssh_key_fingerprint, ssh_key_name):
        if ssh_key_fingerprint:
            return ssh_key_fingerprint
        if ssh_key_name:
            for key in self.api.list_ssh_keys():
                if key['name'] == ssh_key_name:
                    return key['fingerprint']
            raise ModuleError(f"Unable to find ssh key {ssh_key_name}")
        return None

    def get_flavor_id(self, flavor_id, flavor_name):
        if flavor_id and flavor_name:
            raise ModuleError("Both flavor_id and flavor_name are present.")
        if not flavor_id and not flavor_name:
            raise ModuleError('Need either flavor_id or flavor_name.')
        if flavor_name:
            flavor_id = self.api.toolbox.find_cloud_flavor_id_by_name(
                flavor_name=flavor_name,
                region_id=self.region_id,
                must=True
            )
        return flavor_id

    def create_instance(self):
        instance = self.api.post_instance(
            region_id=self.region_id,
            name=self.name,
            flavor_id=self.flavor_id,
            image_id=self.image_id,
            gpn_enabled=self.image_id,
            ipv6_enabled=self.ipv6_enabled,
            ssh_key_fingerprint=self.ssh_key_fingerprint,
            backup_copies=self.backup_copies
        )
        return instance

    def wait_for(self, instance):
        start_time = time.time()
        instance = self.api.get_instances(instance['id'])
        if not self.wait:
            return instance
        while instance['status'] != 'ACTIVE':
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout while waiting instance {instance['id']}"
                    f" to become ACTIVE. Last status was {instance['status']}",
                    timeout=elapsed
                )
            instance = self.api.get_instances(instance['id'])
        return instance

    def run(self):
        instance = self.api.toolbox.find_instance(
            self.instance_id,
            self.name,
            self.region_id,
            must=False
        )
        if instance:
            instance['changed'] = NOT_CHANGED
        else:
            if not self.checkmode:
                instance = self.create_instance()
                instance = self.wait_for(instance)
            else:
                instance = {
                    'info': 'Instance shold be created, '
                            'but check_mode is activated. '
                            'no real instance was created.'
                }
            instance['changed'] = CHANGED
        return instance


class ScCloudComputingInstanceDelete():
    def __init__(
        self,
        endpoint, token,
        instance_id, region_id, name,
        wait, update_interval,
        retry_on_conflicts,
        checkmode
    ):
        self.checkmode = checkmode
        self.api = ScApi(token, endpoint)
        self.region_id = region_id
        self.name = name
        self.instance_id = instance_id
        if update_interval > wait:
            raise ModuleError(
                f"update interval ({update_interval}) "
                f"is longer than wait ({wait})"
            )
        self.wait = wait
        self.update_interval = update_interval
        self.retry_on_conflicts = retry_on_conflicts

    def wait_for_disappearance(self):
        start_time = time.time()
        instance = self.api.toolbox.find_instance(
            self.instance_id,
            self.name,
            self.region_id,
            must=False
        )
        while (instance):
            time.sleep(self.update_interval)
            elapsed = time.time() - start_time
            if elapsed > self.wait:
                raise WaitError(
                    msg=f"Timeout while waiting instance {instance['id']}"
                    f" to disappear. Last status was {instance['status']}",
                    timeout=elapsed
                )
            instance = self.api.toolbox.find_instance(
                self.instance_id,
                self.name,
                self.region_id,
                must=False
            )

    def retry_to_delete(self, instance):
        # pylint: disable=bad-option-value, raise-missing-from
        start_time = time.time()
        while instance:
            try:
                self.api.delete_instance(instance['id'])

            except APIError409:
                if self.retry_on_conflicts:
                    elapsed = time.time() - start_time
                    if elapsed > self.wait:
                        raise WaitError(
                            msg='Timeout retrying delete for'
                                f' instance {instance["id"]}',
                            timeout=elapsed
                        )
                    time.sleep(self.update_interval)
                else:
                    raise
            instance = instance = self.api.toolbox.find_instance(
                self.instance_id,
                self.name,
                self.region_id,
                must=False
            )

    def run(self):
        # pylint: disable=bad-option-value, raise-missing-from
        original_instance = self.api.toolbox.find_instance(
            self.instance_id,
            self.name,
            self.region_id,
            must=False
        )
        instance = original_instance
        if not instance:
            return {
                'changed': False,
                'instance_id': self.instance_id,
                'name': self.name,
                'region_id': self.region_id
            }
        if not self.checkmode:
            instance = self.retry_to_delete(instance)
            self.wait_for_disappearance()
        original_instance['changed'] = CHANGED
        return original_instance


class ScCloudComputingInstancePtr():
    def __init__(
        self,
        endpoint, token,
        state,
        instance_id, name, region_id,
        ip, domain, ttl, priority,
        checkmode
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
            if domain and domain == record['domain']:
                found = True
            if ip and ip == record['ip']:
                found = True
            if found:
                yield record

    def run(self):
        instance = self.api.toolbox.find_instance(
            instance_id=self.instance_id,
            instance_name=self.name,
            region_id=self.region_id,
            must=True
        )
        ptr_records = list(self.api.list_instance_ptr_records(instance['id']))
        if self.state == 'query':
            return {
                'changed': False,
                'ptr_records': list(ptr_records)
            }
        elif self.state == 'present':
            if list(self.find_ptr(ptr_records, self.domain, self.ip)):
                return {
                    'changed': False,
                    'ptr_records': list(ptr_records)
                }
            if self.checkmode:
                return {
                    'changed': True,
                    'ptr_records': list(ptr_records)
                }
            self.api.post_instance_ptr_records(
                instance_id=instance['id'],
                data=self.domain,
                ip=self.ip,
                ttl=self.ttl,
                priority=self.priority
            )
            return {
                'changed': True,
                'ptr_records': list(
                    self.api.list_instance_ptr_records(instance['id'])
                )
            }
        elif self.state == 'absent':
            if not list(self.find_ptr(ptr_records, self.domain, self.ip)):
                return {
                    'changed': False,
                    'ptr_records': list(ptr_records)
                }
            if self.checkmode:
                return {
                    'changed': True,
                    'ptr_records': list(ptr_records)
                }
            for record in self.find_ptr(ptr_records, self.domain, self.ip):
                self.api.delete_instance_ptr_records(
                    instance_id=instance['id'],
                    record_id=record['id']

                )
            return {
                'changed': True,
                'ptr_records': list(
                    self.api.list_instance_ptr_records(instance['id'])
                )
            }
        else:
            raise ModuleError(f"Unknown state={self.state}")


class ScCloudComputingInstanceState:
    def __init__(
        self,
        endpoint, token,
        state,
        instance_id, name, region_id, image_id, image_regexp,
        wait, update_interval,
        checkmode
    ):
        self.api = ScApi(token, endpoint)
        self.state = state
        self.instance_id = self.api.toolbox.find_instance(
            instance_id=instance_id,
            instance_name=name,
            region_id=region_id,
            must=True
        )['id']
        self.image_id = image_id
        self.image_regexp = image_regexp
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def wait_for_statuses(self, status_done, statuses_continue):
        start_time = time.time()
        while self.instance['status'] not in statuses_continue + [status_done]:
            if not self.wait:
                break
            if time.time() > start_time + self.wait:
                raise WaitError(
                    msg=f"Timeout waiting instance {self.instance['id']} "
                        f"status {status_done} or {statuses_continue}. "
                        f"Last state was {self.instance['status']}",
                    timeout=time.time() - start_time
                )
            time.sleep(self.update_interval)
            self.instance = self.api.get_instances(self.instance_id)
        if self.instance['status'] == status_done:
            return True
        else:
            if self.instance['status'] in statuses_continue:
                return False
            else:
                if self.wait:
                    raise WaitError(
                        msg=f"Timeout waiting instance {self.instance['id']} "
                            f"status {status_done}. "
                            f"Last state was {self.instance['status']}",
                        timeout=time.time() - start_time
                    )

    def shutdown(self):
        if self.instance['status'] == 'RESCUE':
            raise ModuleError(
                'Shutdown is not supported in rescue mode.'
            )
        if self.wait_for_statuses(
            status_done='SWITCHED_OFF',
            statuses_continue=['ACTIVE']
        ):
            self.instance['changed'] = False
            return self.instance
        if self.checkmode:
            self.instance['changed'] = True
            return self.instance
        self.api.post_instance_switch_off(self.instance_id)
        self.wait_for_statuses(
            status_done='SWITCHED_OFF',
            statuses_continue=[]
        )
        self.instance = self.api.get_instances(self.instance_id)
        self.instance['changed'] = True
        return self.instance

    def normalize(self):
        if self.wait_for_statuses(
            status_done='ACTIVE',
            statuses_continue=['SWITCHED_OFF', 'RESCUE']
        ):
            self.instance['changed'] = False
            return self.instance
        if self.checkmode:
            self.instance['changed'] = True
            return self.instance
        if self.instance['status'] == 'SWITCHED_OFF':
            self.api.post_instance_switch_on(self.instance_id)
        elif self.instance['status'] == 'RESCUE':
            self.api.post_instance_unrescue(self.instance_id)
        self.wait_for_statuses(
            status_done='ACTIVE',
            statuses_continue=[]
        )
        self.instance = self.api.get_instances(self.instance_id)
        self.instance['changed'] = True
        return self.instance

    def rescue(self):
        if self.image_id or self.image_regexp:
            image_id = self.api.toolbox.find_image_id(
                image_id=self.image_id,
                image_regexp=self.image_regexp,
                region_id=self.instance['region_id'],
                must=True
            )
        else:
            image_id = None
        if self.wait_for_statuses(
            status_done='RESCUE',
            statuses_continue=['ACTIVE', 'SWITCHED_OFF']
        ):
            self.instance['changed'] = False
            return self.instance
        if self.checkmode:
            self.instance['changed'] = True
            return self.instance
        self.api.post_instance_rescue(self.instance_id, image_id)
        self.wait_for_statuses(
            status_done='RESCUE',
            statuses_continue=[]
        )
        self.instance = self.api.get_instances(self.instance_id)
        self.instance['changed'] = True
        return self.instance

    def reboot(self):
        raise NotImplementedError

    def run(self):
        self.instance = self.api.get_instances(self.instance_id)
        if self.state == 'shutdown':
            return self.shutdown()
        elif self.state == 'rescue':
            return self.rescue()
        elif self.state == 'rebooted':
            return self.reboot()
        elif self.state == 'normal':
            return self.normalize()
        else:
            raise ModuleError(f"Unknown state={self.state}")


class ScCloudComputingInstanceReinstall:
    def __init__(
        self,
        endpoint, token,
        instance_id, name, region_id, image_id, image_regexp,
        wait, update_interval,
        checkmode
    ):
        self.api = ScApi(token, endpoint)
        self.instance = self.api.toolbox.find_instance(
            instance_id=instance_id,
            instance_name=name,
            region_id=region_id,
            must=True
        )
        if not image_id and not image_regexp:
            self.image_id = self.instance['image_id']
        else:
            self.image_id = self.api.toolbox.find_image_id(
                image_id=image_id,
                image_regexp=image_regexp,
                region_id=region_id
            )
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    #  copypaste, refactor, TODO
    def wait_for_statuses(self, status_done, statuses_continue):
        start_time = time.time()
        if self.wait:
            time.sleep(self.update_interval)   # workaround around bug in APIs
        while self.instance['status'] not in statuses_continue + [status_done]:
            if not self.wait:
                break
            if time.time() > start_time + self.wait:
                raise WaitError(
                    msg=f"Timeout waiting instance {self.instance['id']} "
                        f"status {status_done} or {statuses_continue}. "
                        f"Last state was {self.instance['status']}",
                    timeout=time.time() - start_time
                )
            time.sleep(self.update_interval)
            self.instance = self.api.get_instances(self.instance['id'])
        if self.instance['status'] == status_done:
            return True
        else:
            if self.instance['status'] in statuses_continue:
                return False
            else:
                if self.wait:
                    raise WaitError(
                        msg=f"Timeout waiting instance {self.instance['id']} "
                            f"status {status_done}. "
                            f"Last state was {self.instance['status']}",
                        timeout=time.time() - start_time
                    )

    def run(self):
        if self.checkmode:
            self.instance['changed'] = True
            return self.instance
        self.api.post_instances_reinstall(
            instance_id=self.instance['id'],
            image_id=self.image_id
        )
        self.wait_for_statuses(
            status_done='ACTIVE',
            statuses_continue=[]
        )
        self.instance['changed'] = True
        return self.instance


class ScCloudComputingInstanceUpgrade:
    def __init__(
        self,
        endpoint, token,
        instance_id, name, region_id,
        flavor_id, flavor_name,
        confirm_upgrade,
        wait, update_interval,
        checkmode
    ):
        self.api = ScApi(token, endpoint)
        self.instance = self.api.toolbox.find_instance(
            instance_id=instance_id,
            instance_name=name,
            region_id=region_id,
            must=True
        )
        self.flavor_id = self.api.toolbox.find_cloud_flavor_id_by_name(
            flavor_id=flavor_id,
            flavor_name=flavor_name,
            region_id=region_id
        )
        self.confirm_upgrade = confirm_upgrade
        self.wait = wait
        self.update_interval = update_interval
        self.checkmode = checkmode

    def run(self):
        if self.flavor_id == self.instance['flavor_id']:
            self.instance['changed'] = False
            return self.instance
        if self.checkmode:
            self.instance['changed'] = True
            return self.instance
        raise NotImplementedError()
        # self.api.post_instances_approve_upgrade(self.instance['id'])
        #     self.wait_for_statuses(
        #         status_done = 'ACTIVE',
        #         statuses_continue = []
        #     )
