# Serverscom Ansible Collection

## Project Overview
Ansible collection providing modules for the Servers.com public API, https://developers.servers.com/api-documentation/v1/
It's used to manage baremetal servers, cloud computing instances, SSH keys, L2 segments, load balancers, and RBS (Remote Block Storage) volumes.

There are two types of baremetal: Enterprise Baremetal (baremetal) and Scalable Baremetal (SBM).

## Structure
- **Location**: Collections is in `ansible_collections/serverscom/sc_api/`. In it:

- **Modules**: `plugins/modules/` - 40+ modules, thin wrappers that parse args and delegate to handler classes
- **Utils**: `plugins/module_utils/`
  - `sc_api.py` - API layer: `ApiHelper` (HTTP/auth/retry/pagination) → `ScApi` (high-level API methods) + `ScApiToolbox` (name/regex lookups)
  - `modules.py` - Handler classes for all non-SBM modules (e.g. `ScCloudComputingInstanceCreate`, `ScL2Segment`, `ScRBSVolumeList`)
  - `sc_sbm.py` - SBM handler classes + resolver functions (`resolve_sbm_server_id`, `resolve_location_id`, etc.)
- **Doc fragments**: `plugins/doc_fragments/sc_sbm.py` - shared `token`/`endpoint` docs (used only by SBM modules; other modules define these inline)

## Key Patterns
1. **Module naming**: `sc_<resource>` or `sc_<resource>_info` (info modules are read-only)
2. **Module structure**: Each module creates a handler class instance and calls `.run()` inside `try/except SCBaseError`, using `e.fail()` on error
3. **API client layers**: `ScApi` (API methods) → `ApiHelper` (HTTP, Bearer auth, retry, pagination) → `ScApiToolbox` (convenience lookups by name/regex)
4. **Error handling**: `APIError400`, `APIError401`, `APIError404`, `APIError409`, `DecodeError` — all carry `correlation_id` and have `.fail()` returning structured dict
5. **Wait/retry**: Handler classes poll API with `retry_rules` (retries on 429 rate-limit and 500); `WaitError` on timeout
6. **Parameters**: All modules require `token` and accept `endpoint`. Action modules often support `wait`/`update_interval`
7. **Module parameter naming:** All `_id` params need `_name` / `_regex` alternatives. Module resolves to IDs internally.
   Examples: `server_id` / `server_hostname` / `server_regex`, `flavor_id` / `flavor_name`, `location_id` / `location_code`

## Testing
- **Sanity/Unit**: `ansible-test sanity/units --requirements --python 3.13` (from `ansible_collections/serverscom/sc_api/`)
- **Integration**: Needs `tests/integration/integration_config.yml` with `SC_TOKEN` (see template). You should not run them.

Libraries: ansible-provided and requests.
CI: Github Actions .github/workflows/tests.yaml

## Module Groups
- **Baremetal**: `sc_baremetal_*`, `sc_dedicated_server_*`
- **Cloud computing**: `sc_cloud_computing_*`
- **SBM (Scalable Baremetal)**: `sc_sbm_*`
- **L2 networking**: `sc_l2_segment*`
- **Load Balancer**: `sc_load_balancer_*` (L4 and L7)
- **RBS (Remote Block Storage)**: `sc_rbs_*`
- **SSH keys**: `sc_ssh_key*`

## Common Dev Commands
```bash
cd ansible_collections/serverscom/sc_api
ansible-test sanity --requirements --python 3.13
ansible-test units --requirements --python 3.13
```
