import argparse
import asyncio
import re
import sys
from typing import List

from google.api_core.exceptions import GoogleAPIError
from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1

DEFAULT_PROJECT_ID = 'my-project'
DEFAULT_ZONE = 'us-central1-a'
DEFAULT_MACHINE_TYPE = 'e2-medium'
DEFAULT_NETWORK_LINK = 'global/networks/default'
DEFAULT_IMAGE_FAMILY = 'debian-11'
DEFAULT_DISK_SIZE_GB = 10
DEFAULT_DISK_TYPE = 'pd-standard'
DEFAULT_BOOT_DISK_AUTO_DELETE = True
DEFAULT_BOOT_DISK_BOOT = True
DEFAULT_STARTUP_SCRIPT_URL = 'https://startup-script-url.com'
DEFAULT_EXTERNAL_IP = 'ephemeral'
DEFAULT_TAGS = ['http-server', 'https-server']
DEFAULT_CREATE_TIMEOUT_SEC = 300


def get_compute_client() -> compute_v1.InstancesClient:
    return compute_v1.InstancesClient()


def get_image_from_family(project: str, family: str) -> compute_v1.Image:
    image_client = compute_v1.ImagesClient()
    newest_image = image_client.get_from_family(project=project, family=family)
    return newest_image


def disk_from_image(
        disk_type: str,
        disk_size_gb: int,
        boot: bool,
        source_image: str,
        auto_delete: bool = DEFAULT_BOOT_DISK_AUTO_DELETE,
) -> compute_v1.AttachedDisk:
    boot_disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = source_image
    initialize_params.disk_size_gb = disk_size_gb
    initialize_params.disk_type = disk_type
    boot_disk.initialize_params = initialize_params
    boot_disk.auto_delete = auto_delete
    boot_disk.boot = boot
    return boot_disk


def wait_for_extended_operation(
        operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = DEFAULT_CREATE_TIMEOUT_SEC
) -> None:
    try:
        result = operation.result(timeout=timeout)
    except GoogleAPIError as e:
        print(f"Error during {verbose_name}: {e}", file=sys.stderr, flush=True)
        print(f"Operation ID: {operation.name}", file=sys.stderr, flush=True)
        raise

    if operation.warnings:
        print(f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True)
        for warning in operation.warnings:
            print(f" - {warning.code}: {warning.message}", file=sys.stderr, flush=True)


def create_instance(
        project_id: str,
        zone: str,
        instance_name: str,
        machine_type: str = DEFAULT_MACHINE_TYPE,
        network_link: str = DEFAULT_NETWORK_LINK,
        image_family: str = DEFAULT_IMAGE_FAMILY,
        disk_size_gb: int = DEFAULT_DISK_SIZE_GB,
        disk_type: str = DEFAULT_DISK_TYPE,
        boot_disk_auto_delete: bool = DEFAULT_BOOT_DISK_AUTO_DELETE,
        boot_disk_boot: bool = DEFAULT_BOOT_DISK_BOOT,
        startup_script_url: str = None,
        external_ip: str = DEFAULT_EXTERNAL_IP,
        tags: List[str] = DEFAULT_TAGS,
) -> compute_v1.Instance:
    compute_client = get_compute_client()

    # Use the network interface provided in the network_link argument.
    network_interface = compute_v1.NetworkInterface()
    network_interface.name = network_link
    if external_ip == 'ephemeral':
        access = compute_v1.AccessConfig()
        access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
        access.name = "External NAT"
        access.network_tier = access.NetworkTier.PREMIUM.name
        network_interface.access_configs = [access]
    elif external_ip == 'none':
        network_interface.access_configs = []
    else:
        access = compute_v1.AccessConfig()
        access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
        access.name = "External NAT"
        access.network_tier = access.NetworkTier.PREMIUM.name
        access.nat_i_p = external_ip
        network_interface.access_configs = [access]

    # Create a boot disk from the most recent image in the given family.
    image = get_image_from_family(project_id, image_family)
    boot_disk = disk_from_image(disk_type, disk_size_gb, boot_disk_boot, image.self_link, boot_disk_auto_delete)

    # Add a startup script URL if provided.
    metadata = compute_v1.Metadata()
    if startup_script_url is not None:
        startup_script = compute_v1.MetadataItems()
        startup_script.key = 'startup-script-url'
        startup_script.value = startup_script_url
        metadata.items = [startup_script]

    # Add the tags.
    instance_tags = compute_v1.Tags()
    instance_tags.items = tags

    # Collect information into the Instance object.
    instance = compute_v1.Instance()
    instance.network_interfaces = [network_interface]
    instance.name = instance_name
    instance.disks = [boot_disk]
    instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"
    instance.metadata = metadata
    instance.tags = instance_tags

    # Prepare the request to insert an instance.
    request = compute_v1.InsertInstanceRequest()
    request.zone = zone
    request.project = project_id
    request.instance_resource = instance

    # Wait for the create operation to complete.
    print(f"Creating the {instance_name} instance in {zone}...")
    operation = compute_client.insert(request=request)
    wait_for_extended_operation(operation, "instance creation")
    print(f"Instance {instance_name} created.")

    return compute_client.get(project=project_id, zone=zone, instance=instance_name)


async def create_multiple_instances(project_id, zone, instance_count,
                                    machine_type=DEFAULT_MACHINE_TYPE,
                                    network_link=DEFAULT_NETWORK_LINK,
                                    image_family=DEFAULT_IMAGE_FAMILY,
                                    disk_size_gb=DEFAULT_DISK_SIZE_GB,
                                    disk_type=DEFAULT_DISK_TYPE,
                                    boot_disk_auto_delete=DEFAULT_BOOT_DISK_AUTO_DELETE,
                                    boot_disk_boot=DEFAULT_BOOT_DISK_BOOT,
                                    startup_script_url=None,
                                    external_ip=DEFAULT_EXTERNAL_IP,
                                    tags=DEFAULT_TAGS):
    image = get_image_from_family(project_id, image_family)

    disks = [disk_from_image(
        disk_type=disk_type,
        disk_size_gb=disk_size_gb,
        boot=boot_disk_boot,
        source_image=image.self_link,
        auto_delete=boot_disk_auto_delete)]

    network_interface = compute_v1.NetworkInterface()
    network_interface.name = network_link

    if external_ip == 'ephemeral':
        access_config = compute_v1.AccessConfig(
            type_='ONE_TO_ONE_NAT',
            name='External NAT',
            network_tier='PREMIUM'
        )
        network_interface.access_configs = [access_config]

    if tags:
        tags = compute_v1.Tags(items=tags)

    instance_client = compute_v1.InstancesClient()
    tasks = []
    for i in range(instance_count):
        instance_name = f"instance-{i + 1}"
        tasks.append(
            asyncio.create_task(
                instance_client.insert(project=project_id, zone=zone, instance_resource=compute_v1.Instance(
                    name=instance_name,
                    machine_type=f"zones/{zone}/machineTypes/{machine_type}",
                    disks=disks,
                    network_interfaces=[network_interface],
                    tags=tags,
                    metadata=compute_v1.Metadata(items=[{
                        'key': 'startup-script-url',
                        'value': startup_script_url,
                    }] if startup_script_url else None)
                ))
            )
        )
    return await asyncio.gather(*tasks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create multiple instances in GCP')
    parser.add_argument('--project-id', type=str, required=True, help='The project ID')
    parser.add_argument('--zone', type=str, required=True, help='The zone to create instances in')
    parser.add_argument('--count', type=int, required=True, help='The number of instances to create')
    parser.add_argument('--machine-type', type=str, default=DEFAULT_MACHINE_TYPE,
                        help='The machine type for the instances')
    parser.add_argument('--network-link', type=str, default=DEFAULT_NETWORK_LINK, help='The network interface to use')
    parser.add_argument('--image-family', type=str, default=DEFAULT_IMAGE_FAMILY,
                        help='The image family to use for the instances')
    parser.add_argument('--disk-size-gb', type=int, default=DEFAULT_DISK_SIZE_GB,
                        help='The size of the boot disk for the instances')
    parser.add_argument('--disk-type', type=str, default=DEFAULT_DISK_TYPE,
                        help='The type of the boot disk for the instances')
    parser.add_argument('--boot-disk-auto-delete', type=bool, default=DEFAULT_BOOT_DISK_AUTO_DELETE,
                        help='Whether to auto-delete the boot disk for the instances')
    parser.add_argument('--boot-disk-boot', type=bool, default=DEFAULT_BOOT_DISK_BOOT,
                        help='Whether the boot disk is a boot disk for the instances')
    parser.add_argument('--startup-script-url', type=str, default=None,
                        help='The URL of the startup script for the instances')
    parser.add_argument('--external-ip', type=str, default=DEFAULT_EXTERNAL_IP,
                        help='The type of external IP address to assign to the instances (ephemeral or None)')
    parser.add_argument('--tags', type=str, nargs='+', default=DEFAULT_TAGS,
                        help='The list of tags to apply to the instances')
    args = parser.parse_args()

    asyncio.run(
        create_multiple_instances(
            project_id=args.project_id,
            zone=args.zone,
            instance_count=args.count,
            machine_type=args.machine_type,
            network_link=args.network_link,
            image_family=args.image_family,
            disk_size_gb=args.disk_size_gb,
            disk_type=args.disk_type,
            boot_disk_auto_delete=args.boot_disk_auto_delete,
            boot_disk_boot=args.boot_disk_boot,
            startup_script_url=args.startup_script_url,
            external_ip=args.external_ip,
            tags=args.tags
        )
    )

'''
python create_instances.py --project-id falra-368206 --zone us-central1-a --count 3 --machine-type t2d-standard-1 --network-link global/networks/default --image-family debian-11 --disk-size-gb 10 --disk-type pd-standard --boot-disk-auto-delete True --boot-disk-boot True --external-ip ephemeral --tags http-server https-server --create-disk "auto-delete=yes,boot=yes,device-name=instance-1,image=projects/debian-cloud/global/images/debian-11-bullseye-v20230206,mode=rw,size=10,type=projects/falra-368206/zones/us-central1-a/diskTypes/pd-standard" --no-shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring --reservation-affinity any
'''
