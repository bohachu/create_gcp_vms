"""
BEFORE RUNNING:
---------------
1. If not already done, enable the Compute Engine API
   and check the quota for your project at
   https://console.developers.google.com/apis/api/compute
2. This sample uses Application Default Credentials for authentication.
   If not already done, install the gcloud CLI from
   https://cloud.google.com/sdk and run
   `gcloud beta auth application-default login`.
   For more information, see
   https://developers.google.com/identity/protocols/application-default-credentials
3. Install the Python client library for Google APIs by running
   `pip install --upgrade google-api-python-client`
"""
from pprint import pprint

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

credentials = GoogleCredentials.get_application_default()

service = discovery.build('compute', 'v1', credentials=credentials)

# Project ID for this request.
project = 'plant-hero'  # TODO: Update placeholder value.

# The name of the zone for this request.
zone = 'us-central1-a'  # TODO: Update placeholder value.

# Name of the instance scoping this request.
instance = 'vm8'  # TODO: Update placeholder value.

current_tags = service.instances().get(project=project, zone=zone, instance=instance).execute()['tags']
print('current_tags', current_tags)
network_tags = ["https-server"]
updated_tags = list(set(current_tags + network_tags))
print('updated_tags', updated_tags)
tags_body = {'tags': {'items': updated_tags}}
request = service.instances().setTags(project=project, zone=zone, instance=instance, body=tags_body)
response = request.execute()

# TODO: Change code below to process the `response` dict:
pprint(response)
