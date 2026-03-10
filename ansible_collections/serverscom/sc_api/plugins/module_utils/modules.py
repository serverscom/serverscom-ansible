from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import env_fallback
from ansible_collections.serverscom.sc_api.plugins.module_utils.api import (
    SCBaseError,
    DEFAULT_API_ENDPOINT,
)


__metaclass__ = type

_ignored = DEFAULT_API_ENDPOINT  # to silence pylint warning, it is reimported

CHANGED = True
NOT_CHANGED = False

AUTH_ARGS = {
    "token": {
        "type": "str",
        "no_log": True,
        "required": True,
        "fallback": (env_fallback, ["SERVERSCOM_API_TOKEN", "SC_TOKEN"]),
    },
    "endpoint": {
        "type": "str",
        "default": DEFAULT_API_ENDPOINT,
        "fallback": (env_fallback, ["SERVERSCOM_API_URL"]),
    },
}


def _retry_rules_for_wait(max_wait, delay):
    RETRY_CODES_WAIT = {
        429,  # Ratelimit, need to wait for next window. If we are unlucky, it' a failure, but nothing to do within wait time.
        500,  # Never observed, but why not?
    }
    # We subsrtract delay, because we wait before first request
    return {
        "codes": RETRY_CODES_WAIT,
        "delay": delay,
        "max_wait": max(0, max_wait - delay),
    }


class ModuleError(SCBaseError):
    def __init__(self, msg):
        self.msg = msg

    def fail(self):
        return {"failed": True, "msg": self.msg}


class WaitError(ModuleError):
    def __init__(self, msg, timeout):
        self.msg = msg
        self.timeout = timeout

    def fail(self):
        return {"failed": True, "timeout": self.timeout, "msg": self.msg}
