import argparse
import re
import sys
import threading
import warnings
from typing import Any, List

from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1


def wait_for_extended_operation(
        operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = 300
) -> Any:
    result = operation.result(timeout=timeout)

    if operation.error_code:
        print(
            f"Error during {verbose_name}: [Code: {operation.error_code}]: {operation.error_message}",
            file=sys.stderr,
            flush=True,
        )
        print(f"Operation ID: {operation.name}", file=sys.stderr, flush=True)
        raise operation.exception() or RuntimeError(operation.error_message)

    if operation.warnings:
        print(f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True)
        for warning in operation.warnings:
            print(f" - {warning.code}: {warning.message}", file=sys.stderr, flush=True)

    return result


def create_instance(
        project_id: str,
        zone: str,
        instance_name: str,
        disks: List[compute_v1.AttachedDisk],
        machine_type: str = "t2d-standard-1",
        network_link: str = "global/networks/default",
        subnetwork_link: str = None,
        internal_ip: str = None,
        external_access: bool = True,
        external_ipv4: str = None,
        accelerators: List[compute_v1.AcceleratorConfig] = None,
        preemptible: bool = False,
        spot: bool = True,
        instance_termination_action: str = "STOP",
        custom_hostname: str = None,
        delete_protection: bool = False,
        metadata: compute_v1.Metadata = None,  # Add metadata parameter here
) -> compute_v1.Instance:
    instance_client = compute_v1.InstancesClient()

    # Use the network interface provided in the network_link argument.
    network_interface = compute_v1.NetworkInterface()
    network_interface.name = network_link
    if subnetwork_link:
        network_interface.subnetwork = subnetwork_link

    if internal_ip:
        network_interface.network_i_p = internal_ip

    if external_access:
        access = compute_v1.AccessConfig()
        access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
        access.name = "External NAT"
        access.network_tier = access.NetworkTier.PREMIUM.name
        if external_ipv4:
            access.nat_i_p = external_ipv4
        network_interface.access_configs = [access]

    # Collect information into the Instance object.
    instance = compute_v1.Instance()
    instance.network_interfaces = [network_interface]
    instance.name = instance_name
    instance.disks = disks

    # add port 80 443
    instance.tags = compute_v1.Tags(items=['http-server', 'https-server'])

    if re.match(r"^zones/[a-z\d\-]+/machineTypes/[a-z\d\-]+$", machine_type):
        instance.machine_type = machine_type
    else:
        instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

    if accelerators:
        instance.guest_accelerators = accelerators

    if preemptible:
        # Set the preemptible setting
        warnings.warn(
            "Preemptible VMs are being replaced by Spot VMs.", DeprecationWarning
        )
        instance.scheduling = compute_v1.Scheduling()
        instance.scheduling.preemptible = True

    if spot:
        # Set the Spot VM setting
        instance.scheduling = compute_v1.Scheduling()
        instance.scheduling.provisioning_model = (
            compute_v1.Scheduling.ProvisioningModel.SPOT.name
        )
        instance.scheduling.instance_termination_action = instance_termination_action

    if custom_hostname is not None:
        # Set the custom hostname for the instance
        instance.hostname = custom_hostname

    if delete_protection:
        # Set the delete protection bit
        instance.deletion_protection = True

    if metadata:
        # Set the metadata for the instance
        instance.metadata = metadata

    # Prepare the request to insert an instance.
    request = compute_v1.InsertInstanceRequest()
    request.zone = zone
    request.project = project_id
    request.instance_resource = instance

    # Wait for the create operation to complete.
    print(f"Creating the {instance_name} instance in {zone}...")

    operation = instance_client.insert(request=request)

    wait_for_extended_operation(operation, "instance creation")

    print(f"Instance {instance_name} created.")
    return instance_client.get(project=project_id, zone=zone, instance=instance_name)


def disk_from_image(
        disk_type: str,
        disk_size_gb: int,
        boot: bool,
        image_project: str,
        image_family: str,
        auto_delete: bool = True,
) -> compute_v1.AttachedDisk():
    disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = f"projects/{image_project}/global/images/family/{image_family}"
    initialize_params.disk_type = disk_type
    initialize_params.disk_size_gb = disk_size_gb
    disk.initialize_params = initialize_params
    # Remember to set auto_delete to True if you want the disk to be deleted when you delete
    # your VM instance.
    disk.auto_delete = auto_delete
    disk.boot = boot
    return disk


def create_from_image(
        project_id: str, zone: str, instance_name: str, image_project: str, image_family: str,
        startup_script: str = None
):
    disk_type = f"zones/{zone}/diskTypes/pd-standard"
    disks = [compute_v1.AttachedDisk()]
    disks[0].boot = True
    disks[0].auto_delete = True
    disks[0].initialize_params = compute_v1.AttachedDiskInitializeParams()
    disks[0].initialize_params.source_image = f"projects/{image_project}/global/images/family/{image_family}"
    disks[0].initialize_params.disk_type = disk_type
    disks[0].initialize_params.disk_size_gb = 10

    if startup_script:
        metadata = compute_v1.Metadata()

        items = compute_v1.types.Items()
        items.key = "startup-script"
        items.value = startup_script
        metadata.items = [items]
        instance = create_instance(project_id, zone, instance_name, disks, metadata=metadata)
    else:
        instance = create_instance(project_id, zone, instance_name, disks)
    return instance


def create_vms(startup_script, vm_number_start=1, vm_number_stop=30):
    threads = []
    for i in range(vm_number_start, vm_number_stop):
        vm_name = f"vm-{i}"
        thread = threading.Thread(target=create_from_image,
                                  args=(
                                      'plant-hero',
                                      'us-central1-a',
                                      vm_name,
                                      'debian-cloud',
                                      'debian-11',
                                      startup_script))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create virtual machines.')
    parser.add_argument('start', type=int, help='start number of virtual machines')
    parser.add_argument('end', type=int, help='end number of virtual machines')
    parser.add_argument('-s', '--script', type=str,
                        default='''#!/bin/bash
                        touch startup_script_success_run.txt
                        sudo apt-get update
                        sudo apt-get install -y docker.io
                        sudo docker run -d -p 80:80 nginx
                        sudo apt install -y python3 python3-pip
                        sudo python3 -m pip install ray
                        ''',
                        help='startup script for virtual machines')
    args = parser.parse_args()

    create_vms(args.script, args.start, args.end)
