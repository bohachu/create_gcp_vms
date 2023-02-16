import argparse
from google.cloud import compute_v1
from google.auth import default
import time


def create_vm(compute, project, zone, name, machine_type, preemptible, image_family, disk_size, startup_script):
    image_response = compute.images().getFromFamily(project=project, family=image_family).execute()
    source_disk_image = image_response['selfLink']

    config = {
        'name': name,
        'machineType': f'zones/{zone}/machineTypes/{machine_type}',
        'scheduling': {
            'preemptible': preemptible,
        },
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                    'diskSizeGb': disk_size,
                }
            }
        ],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],
        'metadata': {
            'items': [{
                'key': 'startup-script',
                'value': startup_script
            }]
        },
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()


def main(project, zone, name, machine_type, preemptible, image_family, disk_size, startup_script):
    creds, project_id = default()
    compute = compute_v1.ComputeClient(credentials=creds)

    create_vm(compute, project, zone, name, machine_type, preemptible, image_family, disk_size, startup_script)

    print('Creating VM. This may take a few minutes.')

    while True:
        instances = compute.instances().list(project=project, zone=zone).execute()
        if 'items' in instances:
            for instance in instances['items']:
                if instance['name'] == name:
                    ip = instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
                    print(f'VM {name} created with IP: {ip}')
                    return
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a GCP VM.')
    parser.add_argument('--project', required=True, help='The GCP project ID.')
    parser.add_argument('--zone', required=True, help='The GCP zone in which to create the VM.')
    parser.add_argument('--name', required=True, help='The name to give the new VM.')
    parser.add_argument('--machine-type', default='e2-micro', help='The machine type for the new VM.')
    parser.add_argument('--preemptible', action='store_true', help='Whether to create a preemptible VM.')
    parser.add_argument('--image-family', default='debian-10', help='The image family for the new VM.')
    parser.add_argument('--disk-size', default=10, type=int, help='The disk size for the new VM in GB.')
    parser.add_argument('--startup-script', default='', help='The startup script to run on the new VM.')
    args = parser.parse_args()

    main(args.project, args.zone, args.name, args.machine_type, args.preemptible, args.image_family, args.disk_size, args.startup_script)

# python3 simple_create_vm.py --project <project-id> --zone <zone> --name <vm-name>
