# Getting started

1. Install/configure venv using requirements.txt.
2. Do not forget to update your Python version in commands below.
3. All ansible-test invocations should happen in `ansible_collections/serverscom/sc_api`.
   This is ansible-test requirement.
4. Installing test dependencies: add `--requirements` to ansible-test during normal calls.

Running sanity checks:

```
ansible-test sanity --requirements --python 3.13
```

Running unit tests:

```
ansible-test units --requirements --python 3.13
```
(if you get odd errors from pytest, don't forget --requirements)

Both unit and sanity checks can work without secrets. There is also a basic integration test, `sc_no_token_tests`, that works without a token and tests the integration between modules and Ansible.

## Local debugging

### Required software

- [just](https://github.com/casey/just) — command runner
- [sops](https://github.com/getsops/sops) — encrypted secrets manager
- GPG (GnuPG) — encryption backend for sops

### GPG key setup

If you don't have a GPG key, generate one:

```
gpg --full-generate-key
```

Choose RSA (default), 4096 bits, and set expiration as needed.

Find your key fingerprint:

```
gpg --list-keys --keyid-format long
```

The fingerprint is the long hex string on the `pub` line (e.g. `ABCD1234EFGH5678...`).

### Initializing secrets

Run `init-secrets` with your GPG fingerprint. This copies the integration
config template, encrypts it with sops, and creates `.secrets/.sops.yaml`:

```
just init-secrets YOUR_GPG_FINGERPRINT
```

Get a token from https://portal.servers.com/. Be careful, some tests cause
significant spending on baremetal servers!

Edit the encrypted config to fill in your real `sc_token` and server IDs.

```
sops --config .secrets/.sops.yaml .secrets/integration_config.sops.yaml
```

### Running integration tests

Use `just run` to execute commands with the decrypted integration config
symlinked into place. The working directory is `ansible_collections/serverscom/sc_api`.

To run a test for a single module:

```
just run ansible-test integration --requirements --python 3.13 sc_rbs_flavors_info
```

The decrypted config is removed automatically when the command finishes.
