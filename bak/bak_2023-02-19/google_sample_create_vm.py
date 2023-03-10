import re
import sys
from typing import Any, List
import warnings

from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials


def get_image_from_family(project: str, family: str, credentials: Credentials) -> compute_v1.Image:
    """
    Retrieve the newest image that is part of a given family in a project.

    Args:
        project: project ID or project number of the Cloud project you want to get image from.
        family: name of the image family you want to get image from.

    Returns:
        An Image object.
    """
    image_client = compute_v1.ImagesClient(credentials=credentials)
    # List of public operating system (OS) images: https://cloud.google.com/compute/docs/images/os-details
    newest_image = image_client.get_from_family(project=project, family=family)
    return newest_image


def disk_from_image(
        disk_type: str,
        disk_size_gb: int,
        boot: bool,
        source_image: str,
        auto_delete: bool = True,
) -> compute_v1.AttachedDisk:
    """
    Create an AttachedDisk object to be used in VM instance creation. Uses an image as the
    source for the new disk.

    Args:
         disk_type: the type of disk you want to create. This value uses the following format:
            "zones/{zone}/diskTypes/(pd-standard|pd-ssd|pd-balanced|pd-extreme)".
            For example: "zones/us-west3-b/diskTypes/pd-ssd"
        disk_size_gb: size of the new disk in gigabytes
        boot: boolean flag indicating whether this disk should be used as a boot disk of an instance
        source_image: source image to use when creating this disk. You must have read access to this disk. This can be one
            of the publicly available images or an image from one of your projects.
            This value uses the following format: "projects/{project_name}/global/images/{image_name}"
        auto_delete: boolean flag indicating whether this disk should be deleted with the VM that uses it

    Returns:
        AttachedDisk object configured to be created using the specified image.
    """
    boot_disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = source_image
    initialize_params.disk_size_gb = disk_size_gb
    initialize_params.disk_type = disk_type
    boot_disk.initialize_params = initialize_params
    # Remember to set auto_delete to True if you want the disk to be deleted when you delete
    # your VM instance.
    boot_disk.auto_delete = auto_delete
    boot_disk.boot = boot
    return boot_disk


def wait_for_extended_operation(
        operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = 300
) -> Any:
    """
    Waits for the extended (long-running) operation to complete.

    If the operation is successful, it will return its result.
    If the operation ends with an error, an exception will be raised.
    If there were any warnings during the execution of the operation
    they will be printed to sys.stderr.

    Args:
        operation: a long-running operation you want to wait on.
        verbose_name: (optional) a more verbose name of the operation,
            used only during error and warning reporting.
        timeout: how long (in seconds) to wait for operation to finish.
            If None, wait indefinitely.

    Returns:
        Whatever the operation.result() returns.

    Raises:
        This method will raise the exception received from `operation.exception()`
        or RuntimeError if there is no exception set, but there is an `error_code`
        set for the `operation`.

        In case of an operation taking longer than `timeout` seconds to complete,
        a `concurrent.futures.TimeoutError` will be raised.
    """
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
        machine_type: str = "n1-standard-1",
        network_link: str = "global/networks/default",
        subnetwork_link: str = None,
        internal_ip: str = None,
        external_access: bool = False,
        external_ipv4: str = None,
        accelerators: List[compute_v1.AcceleratorConfig] = None,
        preemptible: bool = False,
        spot: bool = False,
        instance_termination_action: str = "STOP",
        custom_hostname: str = None,
        delete_protection: bool = False,
        credentials=None
) -> compute_v1.Instance:
    """
    Send an instance creation request to the Compute Engine API and wait for it to complete.

    Args:
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone to create the instance in. For example: "us-west3-b"
        instance_name: name of the new virtual machine (VM) instance.
        disks: a list of compute_v1.AttachedDisk objects describing the disks
            you want to attach to your new instance.
        machine_type: machine type of the VM being created. This value uses the
            following format: "zones/{zone}/machineTypes/{type_name}".
            For example: "zones/europe-west3-c/machineTypes/f1-micro"
        network_link: name of the network you want the new instance to use.
            For example: "global/networks/default" represents the network
            named "default", which is created automatically for each project.
        subnetwork_link: name of the subnetwork you want the new instance to use.
            This value uses the following format:
            "regions/{region}/subnetworks/{subnetwork_name}"
        internal_ip: internal IP address you want to assign to the new instance.
            By default, a free address from the pool of available internal IP addresses of
            used subnet will be used.
        external_access: boolean flag indicating if the instance should have an external IPv4
            address assigned.
        external_ipv4: external IPv4 address to be assigned to this instance. If you specify
            an external IP address, it must live in the same region as the zone of the instance.
            This setting requires `external_access` to be set to True to work.
        accelerators: a list of AcceleratorConfig objects describing the accelerators that will
            be attached to the new instance.
        preemptible: boolean value indicating if the new instance should be preemptible
            or not. Preemptible VMs have been deprecated and you should now use Spot VMs.
        spot: boolean value indicating if the new instance should be a Spot VM or not.
        instance_termination_action: What action should be taken once a Spot VM is terminated.
            Possible values: "STOP", "DELETE"
        custom_hostname: Custom hostname of the new VM instance.
            Custom hostnames must conform to RFC 1035 requirements for valid hostnames.
        delete_protection: boolean value indicating if the new virtual machine should be
            protected against deletion or not.
    Returns:
        Instance object.
    """
    instance_client = compute_v1.InstancesClient(credentials=credentials)

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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create a Compute Engine instance")
    parser.add_argument("project_id", help="ID of the project to create the instance in")
    parser.add_argument("zone", help="Name of the zone to create the instance in")
    parser.add_argument("instance_name", help="Name of the new virtual machine (VM) instance")
    parser.add_argument(
        "--family",
        help="Name of the image family to use when creating the boot disk",
        default="debian-10",
    )
    parser.add_argument(
        "--disk-size-gb",
        help="Size of the new disk in gigabytes",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--disk-type",
        help="Type of disk to create",
        default="pd-standard",
    )
    parser.add_argument(
        "--machine-type",
        help="Machine type of the VM being created",
        default="n1-standard-1",
    )
    parser.add_argument(
        "--network",
        help="Name of the network to use for the new instance",
        default="default",
    )
    parser.add_argument(
        "--subnetwork",
        help="Name of the subnetwork to use for the new instance",
    )
    parser.add_argument(
        "--internal-ip",
        help="Internal IP address to assign to the new instance",
    )
    parser.add_argument(
        "--external-access",
        help="Assign an external IPv4 address to the new instance",
        action="store_true",
    )
    parser.add_argument(
        "--external-ipv4",
        help="External IPv4 address to assign to the new instance",
    )
    parser.add_argument(
        "--accelerator",
        help="Accelerator type to attach to the new instance",
        action="append",
    )
    parser.add_argument(
        "--preemptible",
        help="Create a preemptible VM",
        action="store_true",
    )
    parser.add_argument(
        "--spot",
        help="Create a Spot VM",
        action="store_true",
    )
    parser.add_argument(
        "--instance-termination-action",
        help="Action to take when a Spot VM is terminated",
        choices=["STOP", "DELETE"],
        default="STOP",
    )
    parser.add_argument(
        "--custom-hostname",
        help="Custom hostname of the new VM instance",
    )
    parser.add_argument(
        "--delete-protection",
        help="Enable delete protection for the new VM instance",
        action="store_true",
    )

    args = parser.parse_args()

    image_family = args.family
    disk_size_gb = args.disk_size_gb
    disk_type = f"zones/{args.zone}/diskTypes/{args.disk_type}"
    machine_type = f"zones/{args.zone}/machineTypes/{args.machine_type}"
    network_link = f"global/networks/{args.network}"
    subnetwork_link = None if args.subnetwork is None else f"regions/{args.zone[:-2]}/{args.subnetwork}"
    internal_ip = args.internal_ip
    external_access = args.external_access
    external_ipv4 = args.external_ipv4
    preemptible = args.preemptible
    spot = args.spot
    instance_termination_action = args.instance_termination_action
    custom_hostname = args.custom_hostname
    delete_protection = args.delete_protection

    project_id = args.project_id
    zone = args.zone
    instance_name = args.instance_name

    credentials = service_account.Credentials.from_service_account_file("key.json")
    image = get_image_from_family(project_id, image_family, credentials)
    disk = disk_from_image(disk_type, disk_size_gb, True, image.self_link)
    accelerators = None

    if args.accelerator:
        accelerators = [
            compute_v1.AcceleratorConfig(
                accelerator_count=1,
                **{
                    "accelerator_type": a.split(":")[-1],
                    "guest_accelerator_count": 1,
                },
            )
            for a in args.accelerator
        ]

    create_instance(
        project_id,
        zone,
        instance_name,
        [disk],
        machine_type,
        network_link,
        subnetwork_link,
        internal_ip,
        external_access,
        external_ipv4,
        accelerators,
        preemptible,
        spot,
        instance_termination_action,
        custom_hostname,
        delete_protection,
        credentials
    )


if __name__ == '__main__':
    main()
