from __future__ import (absolute_import, division, print_function)


__metaclass__ = type


DEFAULT_API_ENDPOINT = 'https://api.servers.com/v1'


class SCBaseError(Exception):

    def __init__(self):
        raise NotImplementedError(
            'This exception should not be called directly. Internal error.'
        )

    def fail(self):
        return {
            'failed': True,
            'msg': self.msg
        }


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
            'failed': True,
            'msg': self.msg,
            'api_url': self.api_url,
            'status_code': self.status_code
        }


class DecodeError(APIError):
    pass


# special classes for well-known (and, may be, expected) HTTP/API errors
class APIError401(APIError):
    pass


class APIError404(APIError):
    pass


class APIError409(APIError):
    pass


class ApiHelper():
    def __init__(self, token, endpoint):
        # pylint: disable=bad-option-value, import-outside-toplevel
        # pylint: disable=bad-option-value, raise-missing-from
        try:
            import requests  # noqa
            self.requests = requests
        except ImportError:
            raise APIRequirementsError(
                msg='The requests library is required (python3-requests).'
            )
        self.session = requests.Session()
        self.request = None
        self.endpoint = endpoint
        self.token = token

    def make_url(self, path):
        return self.endpoint + path

    def start_request(
        self,
        method,
        path,
        query_parameters
    ):
        '''return half-backed request'''
        self.request = self.requests.Request(
            method, self.make_url(path), params=query_parameters
        )

    def send_request(self, good_codes):
        '''send a single request/finishes request'''

        self.request.headers['Authorization'] = f'Bearer {self.token}'
        self.request.headers['User-Agent'] = 'ansible-module/sc_api/0.1'
        prep_request = self.request.prepare()
        response = self.session.send(prep_request)
        if response.status_code == 401:
            raise APIError(
                status_code=response.status_code,
                api_url=response.url,
                msg='401 Unauthorized. Check if token is valid.',
            )

        if response.status_code == 404:
            raise APIError404(
                status_code=response.status_code,
                api_url=response.url,
                msg='404 Not Found.',
            )
        if response.status_code == 409:
            raise APIError409(
                status_code=response.status_code,
                api_url=response.url,
                msg='409 Conflict. ' + str(response.content),
            )
        if response.status_code not in good_codes:
            raise APIError(
                status_code=response.status_code,
                api_url=response.url,
                msg=f'API Error: {response.content }',
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
                msg=f'API decoding error: {str(e)}, data: {response.content}',
            )
        return decoded

    def make_get_request(self, path, query_parameters=None):
        'Used for simple GET request without pagination.'
        self.start_request('GET', path, query_parameters)
        return self.decode(self.send_request(good_codes=[200]))

    def make_delete_request(self, path, body, query_parameters, good_codes):
        self.start_request('DELETE', path, query_parameters)
        self.request.body = body
        return self.send_request(good_codes)

    def make_post_request(self, path, body, query_parameters, good_codes):
        self.start_request('POST', path, query_parameters)
        self.request.json = body
        return self.decode(self.send_request(good_codes))

    def is_next(self):
        if self.request:
            return bool(self.request.url)
        return False

    def prepare_next(self, response):
        self.request.url = response.links.get('next', {'url': None})['url']
        self.request.query_params = []

    def make_multipage_request(self, path, query_parameters=None):
        '''Used for GET request with expected pagination. Returns iterator?'''
        self.start_request('GET', path, query_parameters)
        while(self.is_next()):
            response = self.send_request(good_codes=[200])
            list_from_api = self.decode(response)
            for api_object in list_from_api:
                yield api_object
            self.prepare_next(response)


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

class ScApi():
    """Provide functions matching Servers.com Public API."""
    def __init__(self, token, endpoint=DEFAULT_API_ENDPOINT):
        self.api_helper = ApiHelper(token, endpoint)

    def list_locations(self, search_pattern=None):
        if search_pattern:
            query = {'search_pattern': search_pattern}
        else:
            query = None
        return self.api_helper.make_multipage_request(
            path='/locations',
            query_parameters=query
        )

    def list_regions(self):
        return self.api_helper.make_multipage_request(
            '/cloud_computing/regions'
        )

    def get_dedicated_servers(self, server_id):
        return self.api_helper.make_get_request(
            path=f'/hosts/dedicated_servers/{server_id}'
        )

    def list_hosts(self, server_id):
        return self.api_helper.make_multipage_request(
            path='/hosts'
        )

    def post_dedicated_server_reinstall(
        self,
        server_id,
        hostname, operating_system_id, ssh_key_fingerprints, drives
    ):
        return self.api_helper.make_post_request(
            path=f'/hosts/dedicated_servers/{server_id}/reinstall',
            body={
                'hostname': hostname,
                'operating_system_id': operating_system_id,
                'ssh_key_fingerprints': ssh_key_fingerprints,
                'drives': drives
            },
            query_parameters=None,
            good_codes=[202]
        )

    def list_ssh_keys(self):
        return self.api_helper.make_multipage_request('/ssh_keys')

    def post_ssh_keys(self, name, public_key):
        return self.api_helper.make_post_request(
            path='/ssh_keys',
            body=None,
            query_parameters={'name': name, 'public_key': public_key},
            good_codes=[201]
        )

    def delete_ssh_keys(self, fingerprint):
        return self.api_helper.make_delete_request(
            path=f'/ssh_keys/{fingerprint}',
            body=None,
            query_parameters=None,
            good_codes=[204]
        )

    def get_instances(self, instance_id):
        return self.api_helper.make_get_request(
            path=f'/cloud_computing/instances/{instance_id}'
        )

    def get_credentials(self, region_id):
        return self.api_helper.make_get_request(
            path=f'/cloud_computing/regions/{region_id}/credentials'
        )

    def list_flavors(self, region_id):
        return self.api_helper.make_multipage_request(
            path=f'/cloud_computing/regions/{region_id}/flavors'
        )

    def list_images(self, region_id):
        return self.api_helper.make_multipage_request(
            path=f'/cloud_computing/regions/{region_id}/images'
        )

    def list_instances(self, region_id=None):
        region_query = {}
        if region_id is not None:
            region_query['region_id'] = region_id
        return self.api_helper.make_multipage_request(
            path='/cloud_computing/instances',
            query_parameters=region_query
        )

    def post_instances_reinstall(self, instance_id, image_id):
        return self.api_helper.make_post_request(
            path=f'/cloud_computing/instances/{instance_id}/reinstall',
            body=None,
            query_parameters={'image_id': image_id},
            good_codes=[202]
        )

    def post_instance(
        self, region_id, name, flavor_id, image_id,
        gpn_enabled, ipv6_enabled, ssh_key_fingerprint, backup_copies
    ):
        body = {
            'region_id': region_id,
            'name': name,
            'flavor_id': flavor_id,
            'image_id': image_id,
            'gpn_enabled': bool(gpn_enabled),
            'ipv6_enabled': bool(ipv6_enabled),
        }
        if ssh_key_fingerprint:
            body['ssh_key_fingerprint'] = ssh_key_fingerprint
        if backup_copies is not None:
            body['backup_copies'] = backup_copies
        self.api_helper.make_post_request(
            path='/cloud_computing/instances',
            body=body,
            query_parameters=None,
            good_codes=[202]
        )

    def delete_instance(self, instance_id):
        return self.api_helper.make_delete_request(
            path=f'/cloud_computing/instances/{instance_id}',
            query_parameters=None,
            body=None,
            good_codes=[202]
        )
