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
            'msg': 'Unexpected SCBaseError exception. Internal errror.'
        }


class APIError(SCBaseError):
    def __init__(self, msg, api_url, status_code):
        self.api_url = api_url
        self.status_code = status_code
        self.msg = msg

    def fail(self):
        return {
            'failed': True,
            'msg': self.msg,
            'api_url': self.api_url
        }
