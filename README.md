Servers.com ansible modules
===========================

This Ansible collection contains modules to work with public API for servers.com. Documentation for the API is avaiable at https://developers.servers.com.

You need to have an active account in servers.com (https://portal.servers.com). Some operations (new servers, etc) require payments.

Requirements
============
You need ansible 2.9+, python3 and requests library to use those modules.

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

1. You need to issue public API token from https://portal.servers.com/#/profile/api-token
2. Configure `COLLECTION_PATH` (if you are using custom path for collections).
3. Use modules by FQCN (Fully Qualified collection name), f.e. `serverscom.sc_api.sc_ssh_key`
   or by using `collections:` keyword in the play (see examples below).

List of modules
===============

* `sc_baremetal_locations_info` - List of available baremetal locations.
* `sc_cloud_computing_regions_info`- List of cloud computing regions.
* `sc_baremetal_servers_info` - List of baremetal servers.
* `sc_dedicated_server_info` - Information about one dedicated server.
* `sc_dedicated_server_reinstall` - Reinstallation of a dedicated server
* `sc_ssh_key` - SSH key management.
* `sc_ssh_keys_info` - List of registered SSH keys.
* `sc_cloud_computing_flavors_info` - List of flavors in a given region
* `sc_cloud_computing_openstack_credentials` - Credentials to Openstack API
* `sc_cloud_computing_instances_info` - List of cloud computing instances
