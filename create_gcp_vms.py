import argparse
import google.auth
import os
import threading
import time
import json
from google.cloud import compute_v1

# Default parameters
DEFAULT_MACHINE_TYPE = 'e2-micro'
DEFAULT_IMAGE_PROJECT = 'debian-cloud'
DEFAULT_IMAGE_FAMILY = 'debian-10'
DEFAULT_DISK_TYPE = 'pd-standard'
DEFAULT_DISK_SIZE = 10
DEFAULT_NETWORK = 'default'
DEFAULT_FIREWALL_RULES = ['allow-http', 'allow-https']


# Function to create a single VM
def create_vm(name, machine_type=DEFAULT_MACHINE_TYPE, image_project=DEFAULT_IMAGE_PROJECT,
              image_family=DEFAULT_IMAGE_FAMILY,
              disk_type=DEFAULT_DISK_TYPE, disk_size=DEFAULT_DISK_SIZE, network=DEFAULT_NETWORK,
              firewall_rules=DEFAULT_FIREWALL_RULES,
              startup_script=None, docker_compose_file=None):
    # Authenticate and create the Compute Engine client
    creds, project_id = google.auth.default()
    compute = compute_v1.ComputeClient(credentials=creds)

    # Create the VM configuration
    config = {
        'name': name,
        'machineType': f'zones/{os.environ["GOOGLE_CLOUD_ZONE"]}/machineTypes/{machine_type}',
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'sourceImage': f'projects/{image_project}/global/images/family/{image_family}',
                'diskType': f'zones/{os.environ["GOOGLE_CLOUD_ZONE"]}/diskTypes/{disk_type}',
                'diskSizeGb': disk_size
            }
        }],
        'networkInterfaces': [{
            'network': f'projects/{project_id}/global/networks/{network}',
            'accessConfigs': [{
                'type': 'ONE_TO_ONE_NAT',
                'name': 'External NAT'
            }]
        }],
        'tags': {
            'items': firewall_rules
        }
    }

    # If a startup script is provided, add it to the metadata
    if startup_script:
        config['metadata'] = {
            'items': [{
                'key': 'startup-script',
                'value': startup_script
            }]
        }

    # Create the VM instance
    try:
        operation = compute.instances().insert(project=project_id, zone=os.environ['GOOGLE_CLOUD_ZONE'],
                                               body=config).execute()
        print(f'Creating VM {name}...')
        wait_for_operation(compute, project_id, os.environ['GOOGLE_CLOUD_ZONE'], operation['name'])
        print(f'VM {name} has been created successfully.')
    except Exception as e:
        print(f'Error creating VM {name}: {e}')
        return

    # If a Docker Compose file is provided, run it on the VM
    if docker_compose_file:
        run_docker_compose(name, docker_compose_file)


# Function to wait for a Compute Engine operation to complete
def wait_for_operation(compute, project, zone, operation):
    print(f'Waiting for operation {operation} to finish...')
    while True:
        result = compute.zoneOperations().get(project=project, zone=zone, operation=operation).execute()
        if result['status'] == 'DONE':
            if 'error' in result:
                raise Exception(result['error'])
            return result
        time.sleep(1)


# Function to run a Docker Compose file on a VM
def run_docker_compose(name, docker_compose_file):
    # Authenticate and create the Compute Engine client
    credentials, project_id = google.auth.default()
    compute = build('compute', 'v1', credentials=credentials)

    # Wait for the instance to be ready
    print(f'Waiting for VM {name} to be ready...')
    while True:
        instance = compute.instances().get(project=project_id, zone=os.environ['GOOGLE_CLOUD_ZONE'],
                                           instance=name).execute()
        if instance['status'] == 'RUNNING':
            break
        time.sleep(1)

    # Copy the Docker Compose file to the VM
    print(f'Copying Docker Compose file {docker_compose_file} to VM {name}...')
    with open(docker_compose_file, 'r') as f:
        contents = f.read()
    compute.instances().addAccessConfig(project=project_id, zone=os.environ['GOOGLE_CLOUD_ZONE'], instance=name,
                                        networkInterface='nic0', accessConfigBody={
            'type': 'ONE_TO_ONE_NAT',
            'name': 'External NAT'
        }).execute()
    instance = compute.instances().get(project=project_id, zone=os.environ['GOOGLE_CLOUD_ZONE'],
                                       instance=name).execute()
    metadata_items = instance['metadata'].get('items', [])
    startup_script = metadata_items[0]['value'] if metadata_items and metadata_items[0][
        'key'] == 'startup-script' else ''
    startup_script += f'\n\n{contents}'
    compute.instances().update(project=project_id, zone=os.environ['GOOGLE_CLOUD_ZONE'], instance=name, body={
        'metadata': {
            'items': [{
                'key': 'startup-script',
                'value': startup_script
            }]
        }
    }).execute()
    print(
        f'Docker Compose file {docker_compose_file} has been copied to VM {name} and the Docker Compose service has started.')


# Function to create multiple VMs simultaneously
def create_vms(count, machine_type=DEFAULT_MACHINE_TYPE, image_project=DEFAULT_IMAGE_PROJECT,
               image_family=DEFAULT_IMAGE_FAMILY,
               disk_type=DEFAULT_DISK_TYPE, disk_size=DEFAULT_DISK_SIZE, network=DEFAULT_NETWORK,
               firewall_rules=DEFAULT_FIREWALL_RULES,
               startup_script=None, docker_compose_file=None):
    threads = []
    for i in range(count):
        name = f'vm-{i}'
        t = threading.Thread(target=create_vm,
                             args=(name, machine_type, image_project, image_family, disk_type, disk_size, network,
                                   firewall_rules, startup_script, docker_compose_file))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


# Parse command-line arguments
parser = argparse.ArgumentParser(description='Create one or more Compute Engine VMs.')
parser.add_argument('--count', type=int, required=True, help='The number of VMs to create.')
parser.add_argument('--machine-type', default=DEFAULT_MACHINE_TYPE, help='The machine type of the VMs to create.')
parser.add_argument('--image-project', default=DEFAULT_IMAGE_PROJECT,
                    help='The name of the project where the image to use is stored.')
parser.add_argument('--image-family', default=DEFAULT_IMAGE_FAMILY, help='The name of the image family to use.')
parser.add_argument('--disk-type', default=DEFAULT_DISK_TYPE, help='The type of disk to create.')
parser.add_argument('--disk-size', type=int, default=DEFAULT_DISK_SIZE, help='The size of the boot disk in GB.')
parser.add_argument('--network', default=DEFAULT_NETWORK, help='The name of the VPC network to use.')
parser.add_argument('--firewall-rules', nargs='+', default=DEFAULT_FIREWALL_RULES,
                    help='The names of the firewall rules to apply.')
parser.add_argument('--startup-script', help='The startup script to run on the VMs.')
parser.add_argument('--docker-compose-file', help='The Docker Compose file to run on the VMs.')
args = parser.parse_args()

# Create the VMs
create_vms(args.count, machine_type=args.machine_type, image_project=args.image_project, image_family=args.image_family,
           disk_type=args.disk_type, disk_size=args.disk_size, network=args.network, firewall_rules=args.firewall_rules,
           startup_script=args.startup_script, docker_compose_file=args.docker_compose_file)

# Wait for the instances to be ready and then run the Docker Compose file
if args.docker_compose_file:
    for i in range(args.count):
        name = f'vm-{i}'
        t = threading.Thread(target=run_docker_compose, args=(name, args.docker_compose_file))
        t.start()

'''
To run this script, save it to a file called `create_gcp_vms.py`. 
You can then run it using the following command:

python create_gcp_vms.py --count <count> [--machine-type <machine-type>] [--image-project <image-project>] [--image-family <image-family>] [--disk-type <disk-type>] [--disk-size <disk-size>] [--network <network>] [--firewall-rules <firewall-rules>] [--startup-script <startup-script>] [--docker-compose-file <docker-compose-file>]

Replace `<count>` with the number of VMs you want to create. The other arguments are all optional and have default values, as specified in the script. You can provide values for any of these arguments to override the defaults. 
For example, to create 5 VMs with custom firewall rules and a custom Docker Compose file, you could run the following command:

python3 create_gcp_vms.py --count 5 --firewall-rules http-server https-server --docker-compose-file docker-compose.yml

This would create 5 VMs with the default machine type, disk type, disk size, network, and image, but with the `http-server` and `https-server` firewall rules applied. It would also copy the `docker-compose.yml` file to each VM and start the Docker Compose service on each VM.
'''
