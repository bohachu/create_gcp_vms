import google.auth
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from pprint import pprint
from google.cloud import compute_v1

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
compute = compute_v1.InstancesClient()

# 建立防火牆規則
try:
    request = compute.firewalls().insert(project=project, body=firewall_rule)
    response = request.execute()
    pprint(response)
except HttpError as error:
    print(f"建立防火牆失敗：{error}")
