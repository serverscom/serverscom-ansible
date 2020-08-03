from __future__ import (absolute_import, division, print_function)


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
