### Create multiple VMs by GCP
* Create a create_vm.py script that can create n Google Cloud Platform VMs in one go, using the cheapest machine type and default options for preemptibility, firewall rules, disk type, and image family.
* Ensure that the VMs are created simultaneously instead of waiting for one to finish before starting the next.
* Parameterize the script to allow for configuration through the command line interface.
* By default, use the cheapest machine type, preemptibility, and open ports 80 and 443 on the firewall.
* By default, use a 10GB standard disk and the most popular version of Debian.
* Demonstrate how to call the create_vm.py script through a CLI interface.
* Retrieve the private and public IP addresses, VM names, and any other relevant information for all newly created VMs and save the results to an output JSON file that can be used by other programs.
* By default, the new VMs should have a Docker daemon installed and should automatically run a docker-compose up command to execute a docker-compose.yml script that can be passed in as a separate parameter when running create_vm.py.
* The new VMs should be able to automatically reload the original docker-compose.yml script and start it up, even after being restarted.

### Usage
```
python create_gcp_vms.py --count 5 --firewall-rules http-server https-server --docker-compose-file docker-compose.yml
```
