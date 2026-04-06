# Serverscom Ansible Collection

## Project Overview
Ansible collection providing modules for the Servers.com public API, https://developers.servers.com/api-documentation/v1/
It's used to manage baremetal servers, cloud computing instances, SSH keys, L2 segments, load balancers, and RBS (Remote Block Storage) volumes.

There are two types of baremetal: Enterprise Baremetal (dedicated) and Scalable Baremetal (SBM).

## Structure
- **Location**: Collections is in `ansible_collections/serverscom/sc_api/`. In it:

- `plugins/modules/` - 40+ modules, thin wrappers that parse args and delegate to handler classes in module_utils
- `plugins/module_utils/`, code is split per resource type.
   - api.py - API layer: `ApiHelper` (HTTP/auth/retry/pagination) → `ScApi` (high-level API methods) + `ScApiToolbox` (name/regex lookups)
   - modules.py - Common code
   - sbm.py
   - cloud_computing.py
   - dedicated_server.py
   - dedicated_server_ipxe.py
   - l2_segment.py
   - load_balancer.py
   - rbs.py
   - ssh_key.py
- **Doc fragments**: `plugins/doc_fragments/api_auth.py` - shared `token`/`endpoint` docs with env var fallback documentation (used by all modules via `extends_documentation_fragment`)

## Key Patterns
1. **Module naming**: `<resource>` or `<resource>_info` (info modules are read-only). Old `sc_` prefixed names work as aliases via `plugin_routing` in `meta/runtime.yml`, only for old modules. New are created without an alias.
2. **Module structure**: Each module creates a handler class instance and calls `.run()` inside `try/except SCBaseError`, using `e.fail()` on error
3. **API client layers**: `ScApi` (API methods) → `ApiHelper` (HTTP, Bearer auth, retry, pagination) → `ScApiToolbox` (convenience lookups by name/regex)
4. **Error handling**: `APIError400`, `APIError401`, `APIError404`, `APIError409`, `DecodeError` — all carry `correlation_id` and have `.fail()` returning structured dict
5. **Wait/retry**: Handler classes poll API with `retry_rules` (retries on 429 rate-limit and 500); `WaitError` on timeout
6. **Parameters**: All modules require `token` and accept `endpoint`. Both support env var fallback via `env_fallback`: token falls back to `SERVERSCOM_API_TOKEN` then `SC_TOKEN`; endpoint falls back to `SERVERSCOM_API_URL`. Action modules often support `wait`/`update_interval`, common module arguments are called AUTH_ARGS.
7. **Module parameter naming:** All `_id` params need `_name` / `_regex` alternatives. Module resolves to IDs internally.
   Examples: `server_id` / `server_hostname` / `server_regex`, `flavor_id` / `flavor_name`, `location_id` / `location_code`

## Testing
To run quick tests (sanity, unit, non-secret integration tests), run `just quick-tests`

There are other slow and expensive integration tests, do not run them, you don't have access to secrets. Don't try to get access to them.

Libraries: ansible-provided and requests.
CI: Github Actions .github/workflows/tests.yaml
