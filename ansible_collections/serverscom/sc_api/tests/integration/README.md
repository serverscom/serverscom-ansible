How to run integration tests
============================
You need to create a custom `integration_config.yml` file in this directory.
You should never commit the file into the repository (and it's gitignored).

Use `integration_config.yml.template` in the repository root as a starting
point - copy it here and fill in real values for your environment.

Required variables
------------------
* `sc_endpoint` - API endpoint URL
* `sc_token` - API bearer token

Pre-existing resource variables
-------------------------------
These reference resources that must already exist in the account before
running integration tests:

* `existing_server1_id`, `existing_server2_id`, `existing_server3_id` - existing dedicated server IDs
* `non_existing_id` - an ID that does not correspond to any existing resource, but is valid.

Test environment variables
--------------------------
Each test group uses environment-specific IDs, codes, and names.
Update these to match your account's available resources.

**RBS (Block Storage):**
`rbs_test_location_id`, `rbs_test_location_code`, `rbs_test_flavor_id`,
`rbs_test_flavor_name`

**Load Balancer:**
`lb_test_location_id`, `lb_test_upstream_ip1`, `lb_test_upstream_ip2`,
`lb_test_network`

**Cloud Computing:**
`cloud_test_region_id`, `cloud_test_flavor_id`, `cloud_test_flavor_name`,
`cloud_test_ssh_key_fingerprint`, `cloud_test_region_search_pattern`,
`cloud_test_region_search_match`, `cloud_test_region_search_nomatch`

**Baremetal:**
`baremetal_test_location_search_pattern`, `baremetal_test_location_search_match`,
`baremetal_test_location_search_nomatch`, `baremetal_test_os_location_id`,
`baremetal_test_os_location_code`, `baremetal_test_os_server_model_id`,
`baremetal_test_os_server_model_name`

**Dedicated server reinstall:**
`dedicated_test_reinstall_os_id`, `dedicated_test_reinstall_ssh_key_fingerprint`,
`dedicated_test_reinstall_ssh_key_name`

**SBM (Scalable Baremetal):**
`sbm_test_location_code`, `sbm_test_flavor_name`, `sbm_test_os_regex`,
`sbm_test_reinstall_os_name`

See the Justfile recipes (in the root directory of this project) for local development.
