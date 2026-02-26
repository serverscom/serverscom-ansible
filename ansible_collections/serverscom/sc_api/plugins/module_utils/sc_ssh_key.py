from __future__ import absolute_import, division, print_function
from textwrap import wrap
import base64
import hashlib

from ansible_collections.serverscom.sc_api.plugins.module_utils.sc_api import (
    ScApi,
)
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ModuleError,
    CHANGED,
    NOT_CHANGED,
)


__metaclass__ = type


class ScSshKey(object):
    def __init__(
        self,
        endpoint,
        token,
        state,
        name,
        fingerprint,
        public_key,
        labels,
        replace,
        checkmode,
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
        self.labels = labels
        if public_key:
            self.fingerprint = self.extract_fingerprint(public_key)
            if fingerprint and self.fingerprint != fingerprint:
                raise ModuleError(msg="Fingerprint does not match public_key")
        if state == "absent":
            if not any([fingerprint, name, public_key]):
                raise ModuleError(
                    "Need at least one of name, fingerprint, public_key "
                    "for state=absent"
                )
        if state == "present":
            if not public_key:
                raise ModuleError("Need public_key for state=present")
            if not name:
                raise ModuleError("Need name for state=present")

    @staticmethod
    def extract_fingerprint(public_key):
        parts = public_key.split()
        # real key is the largest word in the line
        parts.sort(key=len, reverse=True)
        the_key = base64.decodebytes(parts[0].encode("ascii"))
        digest = hashlib.md5(the_key).hexdigest()
        fingerprint = ":".join(wrap(digest, 2))
        return fingerprint

    @staticmethod
    def classify_matching_keys(key_list, name, fingerprint):
        full_match = []
        partial_match = []
        any_match = []
        for key in key_list:
            if key["name"] == name or key["fingerprint"] == fingerprint:
                any_match.append(key)
                if key["name"] == name and key["fingerprint"] == fingerprint:
                    full_match.append(key)
                else:
                    partial_match.append(key)
        return (full_match, partial_match, any_match)

    def add_key(self):
        if not self.checkmode:
            return self.api.post_ssh_keys(
                name=self.key_name, public_key=self.public_key, labels=self.labels
            )

    def delete_keys(self, key_list):
        if not self.checkmode:
            for key in key_list:
                self.api.delete_ssh_keys(fingerprint=key["fingerprint"])

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
                "Error: Partial match found and no replace option. "
                f"Partially matching keys: {repr(self.partial_match)}"
            )
        if self.partial_match and self.replace:
            self.delete_keys(self.partial_match)
            changed = CHANGED
        if not self.full_match:
            self.add_key()
            changed = CHANGED
        return changed

    def run(self):
        (
            self.full_match,
            self.partial_match,
            self.any_match,
        ) = self.classify_matching_keys(
            self.api.list_ssh_keys(), self.key_name, self.fingerprint
        )
        if self.state == "absent":
            changed = self.state_absent()
        if self.state == "present":
            changed = self.state_present()
        return {"changed": changed}


class ScSshKeysInfo:
    def __init__(self, endpoint, token, label_selector):
        self.api = ScApi(token, endpoint)
        self.label_selector = label_selector

    def run(self):
        return {
            "changed": False,
            "ssh_keys": list(self.api.list_ssh_keys(self.label_selector)),
        }
