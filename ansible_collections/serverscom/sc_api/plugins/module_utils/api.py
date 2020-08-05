from __future__ import (absolute_import, division, print_function)
import itertools


__metaclass__ = type


DEFAULT_API_ENDPOINT = 'https://api.servers.com/v1'


class ModuleError(Exception):
    pass


class APIError(ModuleError):
    def __init__(self, msg, api_url=None, status_code=None):
        self.api_url = api_url
        self.status_code = status_code
        self.msg = msg

    def fail(self):
        return_value = {'failed': True, 'msg': self.msg}
        if self.api_url:
            return_value['api_url'] = self.api_url
        if self.status_code:
            return_value['status_code'] = self.status_code
        return return_value


class DecodeError(APIError):
    pass


# special classes for well-known (and, may be, expected) HTTP/API errors
class APIError401(APIError):
    pass


class APIError404(APIError):
    pass


class Multipage():
    def __init__(self, request):
        pass

    def fetch_more(self):
        pass

    def __next__(self):
        if not self.queue:
            if not self.fetch_more():
                raise StopIteration
            return self.queue.pop()


class Api():
    def __init__(self, token, endpoint=DEFAULT_API_ENDPOINT):
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ModuleError(
                msg='This module needs requests library (python3-requests).')
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'ansible-module/sc_api/0.1'
        self.session.headers['Authorization'] = f'Bearer {token}'
        self.request = None
        self.endpoint = endpoint

    def make_url(self, path):
        return self.endpoint + path

    def prepare_request(
        self,
        path,
        method='GET',
        path_paramter=None,
        query_parameters=None
    ):
        '''return half-backed request'''
        self.request = self.requests.Request(
            method, self.make_url(path), params=query_parameters
        )

    def send_request(self):
        '''send a single request/finishes request'''
        prep_request = self.request.prepare()
        response = self.session.send(prep_request)
        self.request = None
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

        if response.status_code != 200:
            raise APIError(
                status_code=response.status_code,
                api_url=response.url,
                msg=f'API Error: {response.content }',
            )
        return response

    def decode(self, response):
        try:
            decoded = response.json()
        except ValueError as e:
            raise DecodeError(
                api_url=response.url,
                status_code=response.status_code,
                msg=f'API decoding error: {str(e)}, data: {response.content}',
            )
        return decoded

    def make_get_request(self, path, query_parameters):
        'Used for simple GET request without pagination.'
        self.prepare_request(path, path, query_parameters)
        self.decode(self.send_request())

    def is_next(self):
        if self.request:
            return bool(self.request.url)
        return False

    def prepare_next(self, response):
        self.request.url = response.get('next', {'url': None})['url']
        self.request.query_params = []

    def make_multipage_request(self, path, query_parameters):
        '''Used for GET request with expected pagination. Returns iterator?'''
        self.prepare_request(path, path, query_parameters)
        while(self.is_next()):
            response = self.send_request()
            list_from_api = response.decode()
            for api_object in list_from_api:
                yield api_object
            self.prepare_next(response)


class ScDedicatedServerInfo(object):
    def __init__(self, endpoint, token, name, fail_on_absent):
        self.api = Api(token, endpoint)
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
            server_info = self.api.make_get_request(
                path=f'/hosts/dedicated_servers/{self.server_id}',
                query_parameters=None
            )
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


class ScInfo(object):
    def __init__(self, endpoint, token, scope,
                 search_pattern, required_features):
        self.scope = scope
        self.search_pattern = search_pattern
        self.required_features = required_features
        self.API = Api(token, endpoint)

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
        all_locations = self.api.make_multipage_request(
            path='/locations',
            query_parameters={'search_pattern': self.search_pattern}
        )
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

    def regions(self):
        return list(
            self.api.make_multipage_request('/cloud_computing/regions')
        )

    def run(self):
        ret_data = {'changed': False}
        if self.scope in ['all', 'locations']:
            ret_data["locations"] = self.locations()
        if self.scope in ['all', 'regions']:
            ret_data["regions"] = self.regions()
        return ret_data
