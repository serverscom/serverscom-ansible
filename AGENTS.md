# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Ansible collection `serverscom.sc_api` for the Servers.com public API (https://developers.servers.com/api-documentation/v1/).
Manages baremetal servers (Enterprise/dedicated and Scalable/SBM), cloud computing instances, SSH keys, L2 segments, load balancers, and RBS (Remote Block Storage) volumes.

## Collection Location
All collection code lives under `ansible_collections/serverscom/sc_api/`. All `ansible-test` commands must run from that directory.

## Commands

```bash
# Quick tests (sanity + unit, no API token needed)
just quick-tests

# Run only sanity checks
cd ansible_collections/serverscom/sc_api && ansible-test sanity --requirements --python 3.13

# Run all unit tests
cd ansible_collections/serverscom/sc_api && ansible-test units --requirements --python 3.13

# Run a single unit test file (use -- to pass pytest args)
cd ansible_collections/serverscom/sc_api && ansible-test units --requirements --python 3.13 -- tests/unit/plugins/modules/test_sbm_server.py

# Run token-free integration tests (safe, no real API calls)
cd ansible_collections/serverscom/sc_api && ansible-test integration --requirements --python 3.13 sc_no_token_tests

# Run a specific integration target
cd ansible_collections/serverscom/sc_api && ansible-test integration --requirements --python 3.13 <target_name>

# YAML lint
yamllint .

# Build collection tarball
cd ansible_collections/serverscom/sc_api && ansible-galaxy collection build
```

Do NOT run integration tests that require secrets (cloud, BM, L2, LB, RBS, SBM groups) — you don't have access to the API token.

## Architecture

### Module structure
Each module in `plugins/modules/` is a thin wrapper: it parses Ansible args, creates a handler class from `plugins/module_utils/`, calls `.run()`, and catches `SCBaseError` (calling `e.fail()` on error).

### API client layers
`ApiHelper` (HTTP, Bearer auth, retry on 429/500, pagination) → `ScApi` (high-level API methods) → `ScApiToolbox` (name/regex convenience lookups). All in `plugins/module_utils/api.py`.

### Handler classes per resource
Business logic is in `plugins/module_utils/` files: `sbm.py`, `cloud_computing.py`, `dedicated_server.py`, `l2_segment.py`, `load_balancer.py`, `rbs.py`, `ssh_key.py`. Common code (AUTH_ARGS, WaitError, retry helpers) is in `modules.py`.

### Error hierarchy
`SCBaseError` → `APIError` (with `correlation_id`, `status_code`, `api_url`) → `APIError400`/`401`/`404`/`409`/`DecodeError`. Also `ToolboxError`, `ModuleError`, `WaitError`. All have `.fail()` returning a structured dict.

## Key Conventions

1. **Module naming**: `<resource>` or `<resource>_info` (info = read-only). Old `sc_` prefixed names are aliases via `plugin_routing` in `meta/runtime.yml` — new modules must NOT get an `sc_` alias.
2. **Parameters**: All modules use `AUTH_ARGS` (token + endpoint with `env_fallback`). Action modules add `wait`/`update_interval`. All `_id` params need `_name`/`_regex` alternatives resolved internally.
3. **Doc fragments**: `plugins/doc_fragments/api_auth.py` — all modules use `extends_documentation_fragment: serverscom.sc_api.api_auth`.
4. **Action groups**: New modules must be added to the `api` action group in `meta/runtime.yml`.
5. **Unit tests**: In `tests/unit/plugins/modules/`. Tests mock `ScApi` and exercise handler classes directly (not through AnsibleModule). Use `mock` library + pytest.
6. **Integration tests**: In `tests/integration/targets/<module_name>/tasks/main.yaml`. Each target is a standalone Ansible playbook.
7. **CI matrix**: Tests against ansible-core 2.18–2.20, Python 3.13–3.14. CI config in `.github/workflows/tests.yaml`.
8. **Libraries**: Only `ansible` builtins and `requests`. No other third-party deps.
9. **Linting**: yamllint with `line-length: disable` (see `.yamllint`).