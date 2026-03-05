Ansible modules for Servers.com Public API
==========================================

This Ansible collection contains modules to work with the public API for servers.com. Documentation for the API is available at https://developers.servers.com.

You need to have an active account in servers.com (https://portal.servers.com). Some operations (new servers and instances, etc) require payments.

Requirements
============
The modules try to support Ansible 2.9 or higher, but actual tests are done using currently supported versions of Ansible and Python.

You need the requests library for modules to work.

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

1. You need to issue a public API token from https://portal.servers.com/#/profile/api-token. You need an R/W token for
   doing any changes or ordering new resources.
   The token can be passed as environment variable (`SC_TOKEN`) or as module parameter `token` (if both are set, `token` wins).
2. Configure `COLLECTION_PATH` (if you are using custom path for collections).
3. Use modules by FQCN (Fully Qualified Collection Name), e.g. `serverscom.sc_api.sc_ssh_key`
   or by using `collections:` keyword in the play.

You can see documentation for individual modules by calling (after installation) `ansible-doc module_name`, e.g. `ansible-doc sc_ssh_key`.

Notes:

* Resources created with modules will be billed at current prices.
* Requests to the API are rate-limited; contact support if you have high usage.

You can see documentation for individual modules by calling (after installation) `ansible-doc module_name`, f.e. `ansible-doc sc_ssh_key`.

List of modules
===============

**Baremetal Servers**
(Includes dedicated servers, SBM servers and kubernetes nodes)

* `sc_baremetal_locations_info` - List of available baremetal locations
* `sc_baremetal_servers_info` - List of baremetal servers
* `sc_baremetal_os_list` - List of the available OS options for a specific baremetal location and server model

**Dedicated Servers**
(also known as Enterprise Baremetal Servers)

* `sc_dedicated_server_info` - Information about one dedicated server
* `sc_dedicated_server_reinstall` - Reinstallation of dedicated servers
* `sc_dedicated_server_power` - Power management for dedicated baremetal servers

**Cloud Computing**

* `sc_cloud_computing_regions_info` - List of cloud computing regions
* `sc_cloud_computing_flavors_info` - List of flavors in a given region
* `sc_cloud_computing_images_info` - List of available images for cloud computing
* `sc_cloud_computing_instances_info` - List of cloud computing instances
* `sc_cloud_computing_instance_info` - Information about a specific cloud computing instance
* `sc_cloud_computing_instance` - Create/delete/reinstall/upgrade cloud computing instance
* `sc_cloud_computing_instance_state` - Manage shutdown/rescue/reboot state for cloud computing instance
* `sc_cloud_computing_instance_ptr` - Manage PTR records for cloud computing instances
* `sc_cloud_computing_openstack_credentials` - Obtain credentials for OpenStack API access

**SSH Keys**

* `sc_ssh_key` - SSH key management
* `sc_ssh_keys_info` - List of registered SSH keys

**L2 Segments (Network)**

* `sc_l2_segments_info` - List of existing L2 segments
* `sc_l2_segment_info` - Information about a specific L2 segment
* `sc_l2_segment` - Creation/deletion/membership modification for L2 segments
* `sc_l2_segment_aliases` - Add and remove IP addresses to/from L2 segments

**Load Balancers**

* `sc_load_balancer_instances_list` - List load balancer instances
* `sc_load_balancer_instance_info` - Information about a specific load balancer instance
* `sc_load_balancer_instance_l4` - Manage L4 (TCP/UDP) load balancing rules
* `sc_load_balancer_instance_l7` - Manage L7 (HTTP/HTTPS) load balancing rules

**RBS (Remote Block Storage)**

* `sc_rbs_flavors_info` - List available RBS storage flavors
* `sc_rbs_volume` - Create/delete RBS volumes
* `sc_rbs_volume_info` - Information about RBS volumes
* `sc_rbs_volume_credentials_reset` - Reset credentials for RBS volumes

**SBM (Scalable Baremetal)**

* `sc_sbm_servers_info` - List of SBM servers with optional filtering
* `sc_sbm_server` - Create/delete SBM (Scalable Baremetal) servers
* `sc_sbm_server_info` - Information about a specific SBM server
* `sc_sbm_server_power` - Power on/off/cycle operations for SBM servers
* `sc_sbm_server_reinstall` - Reinstall OS on SBM servers
* `sc_sbm_server_ptr_info` - Query PTR records for SBM servers
* `sc_sbm_server_ptr` - Manage PTR records for SBM servers
* `sc_sbm_server_labels` - Update labels on SBM servers
* `sc_sbm_server_networks_info` - List/get networks for SBM servers
* `sc_sbm_server_network` - Create/delete networks for SBM servers
* `sc_sbm_flavor_models_info` - List of available SBM flavor models per location
* `sc_sbm_os_list` - List of the available OS options for SBM servers by location and flavor model
