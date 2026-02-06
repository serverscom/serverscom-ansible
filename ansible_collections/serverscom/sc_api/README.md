Ansible modules for Servers.com Public API
==========================================

This Ansible collection contains modules to work with public API for servers.com. Documentation for the API is avaiable at https://developers.servers.com.

You need to have an active account in servers.com (https://portal.servers.com). Some operations (new servers and instances, etc) require payments.

Requirements
============
You need ansible 2.9+, python 3.6 or newer and requests library to use those modules.

Installation
============

From Ansible Galaxy:
```
ansible-galaxy collection install serverscom.sc_api
```

From this repository:
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

1. You need to issue a public API token from https://portal.servers.com/#/profile/api-token. It's used as `token` parameter for all modules.
2. Configure `COLLECTION_PATH` (if you are using custom path for collections).
3. Use modules by FQCN (Fully Qualified collection name), f.e. `serverscom.sc_api.sc_ssh_key`
   or by using `collections:` keyword in the play.

You can see documentation for individual modules by calling (after installation) `ansible-doc module_name`, f.e. `ansible-doc sc_ssh_key`.

List of modules
===============

* `sc_baremetal_locations_info` - List of available baremetal locations
* `sc_cloud_computing_regions_info`- List of cloud computing regions
* `sc_baremetal_servers_info` - List of baremetal servers
* `sc_baremetal_os_list` - List of the available OS options for the specific region and dedicated server model or server ID
* `sc_dedicated_server_info` - Information about one dedicated server
* `sc_dedicated_server_reinstall` - Reinstallation of servers
* `sc_ssh_key` - SSH key management
* `sc_ssh_keys_info` - List of registered SSH keys
* `sc_cloud_computing_regions_info` - Lisf of cloud computing regions
* `sc_cloud_computing_flavors_info` - List of flavors in a given region
* `sc_cloud_computing_openstack_credentials` - Credentials to Openstack API
* `sc_cloud_computing_instances_info` - List of cloud computing instances
* `sc_cloud_computing_instance_info` - Information about specific instance
* `sc_cloud_computing_images_info` - Information about images for cloud computing
* `sc_cloud_computing_flavors_info` - Information about flavors for cloud computing
* `sc_cloud_computing_instance` - Create/delete/reinstall/upgrade instance
* `sc_cloud_computing_instance_ptr` - Manage PTR records for cloud computing instances
* `sc_cloud_computing_instance_state` - Manage shutdown/rescue/rebooted state for instance
* `sc_l2_segment_info` - information about L2 segment
* `sc_l2_segments_info` - list of existing L2 segments
* `sc_l2_segment` - Creation/delelition/membership modification for L2 segments
* `sc_l2_segment_aliases` - Adding and removing IP addresses to/from L2 segments
* `sc_sbm_server` - Create/delete SBM (Scalable Baremetal) servers
* `sc_sbm_server_info` - Information about a Scalable Baremetal (SBM) server
* `sc_sbm_servers_info` - List of SBM servers with optional filtering
* `sc_sbm_server_power` - Power on/off/cycle operations for SBM servers
* `sc_sbm_server_reinstall` - Reinstall OS on SBM servers
* `sc_sbm_server_ptr` - Manage PTR records for SBM servers
* `sc_sbm_server_labels` - Update labels on SBM servers
* `sc_sbm_server_network` - Create/delete networks for SBM servers
* `sc_sbm_server_networks_info` - List/get networks for SBM servers
* `sc_sbm_flavor_models_info` - List of available SBM flavor models per location
* `sc_sbm_os_list` - List of the available OS options for SBM servers by location and flavor model

