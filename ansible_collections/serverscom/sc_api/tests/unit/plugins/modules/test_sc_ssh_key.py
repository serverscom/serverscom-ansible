# Copyright (c) 2020 Servers.com
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
from ansible_collections.serverscom.sc_api.plugins.module_utils.modules import (
    ScSshKey,
)  # noqa


__metaclass__ = type


def test_extract_fingerprint():
    example_line = "ssh-dss AAAAB3NzaC1kc3MAAACBAItIoLYw/bzUTxi3J6e1xIbh+A4sw7gISo3b1mVBRN9Ri2ZFNG6Ly2ICmDzsi2v7itWJM0Dfuy4t+hQ6YS3qkBPIdhqFjX71kitQLmIxIqHNi4907AWko2YRGAaARHLJtpfG7sv8jrGDGVZfNcoIlZBM6558+5S6yFtRfhy7I41bAAAAFQD6dMEZZ0yAyO+q+vtQq4QqD5owywAAAIBq4pbyP+KDlayxG/+ImVLcpluJdz8rYILKoAcHxYj5baGn4Lmu5nhcCanjZ8LA2lk8f2YNK44hYRmfd2ZgfxuDEoliYBAqf00miFTSrUdQVZQNYaHO1IytBp1ECPopmzVe7wDkvk+3z1L0LeFepIpCQAOxYerEJ2gTt75Djr/gqAAAAIBEfGC+L06OcHVj3up6GAJg0AK0udjyravBnBzau6BLZivkA3WYy1sIdoRhIegMmy7zbOG2ajTsARxwZNCYjDZELt8tTNuc1DGAMOx1bQgkAE9VCtuuGEhiOSipgefSLre2lDo720aZSOXiwIxVBHo9FEH8D1Y0NO8oRSw2f5z0xg== tail@message"  # noqa
    # extracted by ssh-keygen -E md5 -l -f key.pub
    expected_digest = "2a:aa:58:61:88:b3:b0:d9:a5:cf:46:4d:75:b1:15:b7"
    assert ScSshKey.extract_fingerprint(example_line) == expected_digest


KEY1 = {
    "name": "iso-test",
    "fingerprint": "d5:77:48:ee:2f:e7:5e:f4:66:49:98:99:0e:7e:59:78",
}

KEY2 = {
    "name": "iso-test1",
    "fingerprint": "e8:ef:4f:5e:f3:75:e2:c8:6c:66:98:9b:9c:a7:25:f7",
}

KEY3 = {
    "name": "1ea1c330-daee-11ea-ad4c-033b3ea18cbf",
    "fingerprint": "ed:83:d3:30:65:8f:a6:71:34:49:c5:a3:c4:a1:a7:cb",
}

KEY_NOT = {
    "name": "no-such-key",
    "fingerprint": "ff:ff:ff:ff:ff:ff:ff:ff:ff:ff:ff:ff:ff:ff:ff:ff",
}


KEYS_EXAMPLE_1 = [KEY1, KEY2, KEY3]


def test_classify_matching_keys_trivial():
    assert ScSshKey.classify_matching_keys([], None, None) == ([], [], [])


def test_classify_matching_keys_nomatch():
    assert ScSshKey.classify_matching_keys(
        KEYS_EXAMPLE_1, KEY_NOT["name"], KEY_NOT["fingerprint"]
    ) == ([], [], [])


def test_classify_matching_keys_simple_match():
    assert ScSshKey.classify_matching_keys(
        KEYS_EXAMPLE_1, KEY1["name"], KEY1["fingerprint"]
    ) == ([KEY1], [], [KEY1])


def test_classify_matching_keys_partial_match1():
    assert ScSshKey.classify_matching_keys(
        KEYS_EXAMPLE_1, KEY_NOT["name"], KEY2["fingerprint"]
    ) == ([], [KEY2], [KEY2])


def test_classify_matching_keys_partial_match2():
    assert ScSshKey.classify_matching_keys(
        KEYS_EXAMPLE_1, KEY1["name"], KEY2["fingerprint"]
    ) == ([], [KEY1, KEY2], [KEY1, KEY2])
