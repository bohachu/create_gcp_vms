from pprint import pprint

import google.auth
from googleapiclient import discovery
from googleapiclient.errors import HttpError


def create_firewall(project):
    # 取得預設的憑證
    # credentials, project = google.auth.default()

    # 設定防火牆規則
    firewall_name = "allow-http-https"
    network_name = "default"
    priority = 1000
    ip_protocol = "tcp"
    ports = ["80", "443"]
    source_range = "0.0.0.0/0"
    firewall_rule = {
        "name": firewall_name,
        "network": f"projects/{project}/global/networks/{network_name}",
        "priority": priority,
        "direction": "INGRESS",
        "allowed": [
            {
                "IPProtocol": ip_protocol,
                "ports": ports
            }
        ],
        "sourceRanges": [source_range]
    }

    # 建立 Compute Engine API 的 client
    # compute = discovery.build("compute", "v1", credentials=credentials)

    # compute = compute_v1.InstancesClient()

    # credentials = GoogleCredentials.get_application_default()

    creds, project_id = google.auth.default()
    service = discovery.build('compute', 'v1', credentials=creds)

    # 建立防火牆規則
    try:
        request = service.firewalls().insert(project=project, body=firewall_rule)
        response = request.execute()
        pprint(response)
    except HttpError as error:
        print(f"建立防火牆失敗：{error}")


import argparse


def main():
    # 建立解析器
    parser = argparse.ArgumentParser(description="Create a firewall rule to allow HTTP and HTTPS traffic")

    # 新增參數
    parser.add_argument("--project", type=str, help="The ID of the Google Cloud project")

    # 解析參數
    args = parser.parse_args()

    # 取得 project 參數值
    project = args.project
    if project is None:
        # 如果沒有指定 project，就使用預設憑證取得的 project
        _, project = google.auth.default()
    create_firewall(project)


if __name__ == '__main__':
    main()
