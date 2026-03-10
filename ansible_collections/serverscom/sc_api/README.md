Ansible modules for Servers.com Public API
==========================================

This Ansible collection contains modules to work with the public API for [Servers.com](https://servers.com). Documentation for the API is available at https://developers.servers.com.

You need to have an active account in servers.com (https://portal.servers.com). Some operations (new servers and instances, etc) require payments.

Requirements
============
The modules try to support Ansible 2.9 or higher, but actual tests are done using currently supported versions of Ansible and Python.

You need the `requests` library for modules to work.

Installation
============

From Ansible Galaxy:
```
ansible-galaxy collection install serverscom.sc_api
```

From this repository:

Download latest release from Github Releases, and install it:

```
ansible-galaxy collection install https://github.com/serverscom/serverscom-ansible/... tar.gz
```

Manually building collection
============================

```
git clone https://github.com/serverscom/serverscom-ansible.git
cd ansible_collections/serverscom/sc_api
ansible-galaxy collection build
```


Usage
=====

You need to issue a public API token from https://portal.servers.com/iam/api-tokens. You need an R/W token for
doing any changes or ordering new resources.
The token can be passed as environment variable (`SERVERSCOM_API_TOKEN` or `SC_TOKEN`) or as module parameter `token`.
Precedence: `token` parameter > `SERVERSCOM_API_TOKEN` > `SC_TOKEN`.

You can see documentation for individual modules by calling (after installation) `ansible-doc module_name`, e.g. `ansible-doc serverscom.sc_api.ssh_key`.

Notes:

* Resources created with modules will be billed at current prices.
* Requests to the API are rate-limited; contact support if you have high usage.

Old module names with `sc_` prefix (e.g. `serverscom.sc_api.sc_ssh_key`) continue to work as aliases.

List of modules
===============

**Baremetal Servers**
(Includes dedicated servers, SBM servers and kubernetes nodes)

* `baremetal_locations_info` - List of available baremetal locations
* `baremetal_servers_info` - List of baremetal servers
* `baremetal_os_list` - List of the available OS options for a specific baremetal location and server model

**Dedicated Servers**
(also known as Enterprise Baremetal Servers)

* `dedicated_server_info` - Information about one dedicated server
* `dedicated_server_reinstall` - Reinstallation of dedicated servers
* `dedicated_server_power` - Power management for dedicated baremetal servers

**Cloud Computing**

* `cloud_computing_regions_info` - List of cloud computing regions
* `cloud_computing_flavors_info` - List of flavors in a given region
* `cloud_computing_images_info` - List of available images for cloud computing
* `cloud_computing_instances_info` - List of cloud computing instances
* `cloud_computing_instance_info` - Information about a specific cloud computing instance
* `cloud_computing_instance` - Create/delete/reinstall/upgrade cloud computing instance
* `cloud_computing_instance_state` - Manage shutdown/rescue/reboot state for cloud computing instance
* `cloud_computing_instance_ptr` - Manage PTR records for cloud computing instances
* `cloud_computing_openstack_credentials` - Obtain credentials for OpenStack API access

**SSH Keys**

* `ssh_key` - SSH key management
* `ssh_keys_info` - List of registered SSH keys

**L2 Segments (Network)**

* `l2_segments_info` - List of existing L2 segments
* `l2_segment_info` - Information about a specific L2 segment
* `l2_segment` - Creation/deletion/membership modification for L2 segments
* `l2_segment_aliases` - Add and remove IP addresses to/from L2 segments

**Load Balancers**

* `load_balancer_instances_list` - List load balancer instances
* `load_balancer_instance_info` - Information about a specific load balancer instance
* `load_balancer_instance_l4` - Manage L4 (TCP/UDP) load balancing rules
* `load_balancer_instance_l7` - Manage L7 (HTTP/HTTPS) load balancing rules

**RBS (Remote Block Storage)**

* `rbs_flavors_info` - List available RBS storage flavors
* `rbs_volume` - Create/delete RBS volumes
* `rbs_volume_info` - Information about RBS volumes
* `rbs_volume_credentials_reset` - Reset credentials for RBS volumes

**SBM (Scalable Baremetal)**

* `sbm_servers_info` - List of SBM servers with optional filtering
* `sbm_server` - Create/delete SBM (Scalable Baremetal) servers
* `sbm_server_info` - Information about a specific SBM server
* `sbm_server_power` - Power on/off/cycle operations for SBM servers
* `sbm_server_reinstall` - Reinstall OS on SBM servers
* `sbm_server_ptr_info` - Query PTR records for SBM servers
* `sbm_server_ptr` - Manage PTR records for SBM servers
* `sbm_server_labels` - Update labels on SBM servers
* `sbm_server_networks_info` - List/get networks for SBM servers
* `sbm_server_network` - Create/delete networks for SBM servers
* `sbm_flavor_models_info` - List of available SBM flavor models per location
* `sbm_os_list` - List of the available OS options for SBM servers by location and flavor model
