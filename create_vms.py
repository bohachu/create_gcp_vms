import concurrent.futures
from typing import List
from create_from_snapshot import create_from_snapshot


def create_vm_helper(project_id: str, zone: str, vm_name: str, snapshot_link: str) -> str:
    instance = create_from_snapshot(project_id, zone, vm_name, snapshot_link)
    return instance.network_interfaces[0].network_i_p


def create_vms(project_id: str, zone: str, snapshot_link: str, num_vms: int) -> List[str]:
    vm_names = [f"vm-{i + 1}" for i in range(num_vms)]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_vm_name = {executor.submit(create_vm_helper, project_id, zone, vm_name, snapshot_link): vm_name for
                             vm_name in vm_names}
        ip_addresses = []
        for future in concurrent.futures.as_completed(future_to_vm_name):
            vm_name = future_to_vm_name[future]
            try:
                ip_address = future.result()
                ip_addresses.append(ip_address)
                print(f"{vm_name} created with IP address {ip_address}")
            except Exception as e:
                print(f"{vm_name} generated an exception: {e}")
    return ip_addresses


if __name__ == '__main__':
    project_id = "plant-hero"
    zone = "us-central1-a"
    snapshot_link = "projects/plant-hero/global/snapshots/snapshot-5-05"
    num_vms = 30
    ip_addresses = create_vms(project_id, zone, snapshot_link, num_vms)
