from __future__ import (absolute_import, division, print_function)
import itertools


__metaclass__ = type


DEFAULT_API_ENDPOINT = 'https://api.servers.com/v1'


class APIError(Exception):
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


class APIError404(APIError):
    pass


class API(object):
    def __init__(self, endpoint, token):
        self.endpoint = endpoint
        self.token = token
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise APIError(msg='This module needs requests library.')

    def start_request(self, path, query):
        req = self.requests.Request('GET', self.endpoint + path, params=query)
        req.headers['Authorization'] = f'Bearer {self.token}'
        return req

    def send_and_decode(self, request):
        session = self.requests.Session()
        prep_request = request.prepare()
        response = session.send(prep_request)
        if response.status_code == 401:
            raise APIError(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg='401 Unauthorized. Check if token is valid.',
            )
        if response.status_code == 404:
            raise APIError404(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg='404 Not Found.',
            )

        if response.status_code != 200:
            raise APIError(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg=f'API Error: {response.content }',
            )
        try:
            decoded = response.json()
        except ValueError as e:
            raise APIError(
                status_code=response.status_code,
                api_url=prep_request.url,
                msg=f'API decoding error: {str(e)}, data: {response.content}',
            )
        return decoded


class ScDedicatedServerInfo(object):
    def __init__(self, endpoint, token, name, fail_on_absent):
        self.API = API(endpoint, token)
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
        req = self.API.start_request(
            path=f'/hosts/dedicated_servers/{self.server_id}',
            query=None
        )
        try:
            server_info = self.API.send_and_decode(req)
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


class MultiPage(object):

    per_page = 100

    def __init__(self, request):
        self.request = request
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise APIError(msg='This module needs requests library.')

    def __iter__(self):
        self.session = self.requests.Session()
        self.next = self.request
        self.next.params.update({'per_page': self.per_page})
        return self

    def __next__(self):
        if self.next.url:
            prep_req = self.next.prepare()
            resp = self.session.send(prep_req)
            if resp.status_code == 401:
                raise APIError(
                    status_code=resp.status_code,
                    api_url=self.next.url,
                    msg='401 Unauthorized. Check if token is valid.',
                )
            if resp.status_code != 200:
                raise APIError(
                    status_code=resp.status_code,
                    api_url=self.next_url,
                    msg=f'API Error: {resp.content }',
                )
            self.next.url = resp.links.get('next', {'url': None})['url']
            try:
                return resp.json()
            except ValueError as e:
                raise APIError(
                    status_code=resp.status_code,
                    api_url=self.next_url,
                    msg=f'API decoding error: {str(e)}, data: {resp.content}',
                )
        else:
            raise StopIteration


class ScInfo(object):
    def __init__(self, endpoint, token, scope,
                 search_pattern, required_features):
        self.scope = scope
        self.search_pattern = search_pattern
        self.required_features = required_features
        self.API = API(endpoint, token)

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
        req = self.API.start_request(
            path='/locations',
            query={'search_pattern': self.search_pattern}
        )
        all_locations = list(itertools.chain.from_iterable(MultiPage(req)))
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
        req = self.API.start_request(
            path='/cloud_computing/regions',
            query={'search_pattern': self.search_pattern}
        )
        return list(itertools.chain.from_iterable(MultiPage(req)))

    def run(self):
        ret_data = {'changed': False}
        if self.scope in ['all', 'locations']:
            ret_data["locations"] = self.locations()
        if self.scope in ['all', 'regions']:
            ret_data["regions"] = self.regions()
        return ret_data
