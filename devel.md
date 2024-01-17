# Getting started

1. Install/configure venv using requirements.txt.
2. Do not forget to update your python version in commands below.
3. All ansible-test invocations should happen in `ansible_collections/serverscom/sc_api`.
   This is ansible-test requirement.
4. Installing test dependencies: add `--requirements` to ansible-test during normal calls.

Running sanity checks:

```
ansible-test sanity --requirements --python 3.11
```

unit tests:

```
ansible-test units --requirements --python 3.11
```
(if you get odd errors from pytest, don't forget --requirements)

Both unit and sanity checks can work without secrets.

# Integration tests

To run integration tests you need to generate your own config at
`ansible_collections/serverscom/sc_api/tests/integration/integration_config.yml`
(this location is odd, but it's the single place where ansible-test permits any side
causes into test playbooks)

See example in `integration_config.yml.template`.

Please, pay attention,
you need at least 3 baremetal servers to run tests for baremetal modules.

The main secret you get is SC_TOKEN, which is token to access servers.com API.

At the time of writing you could get one from here: https://portal.servers.com/profile/api-tokens

Please be careful, some tests will cause significant financial spendings. They also will reinstall baremetal servers, so you should dedicate servers for those testing exlusively.
