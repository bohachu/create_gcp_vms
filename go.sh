git pull
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
#python3 create_gcp_vms.py --project-id falra-368206 --zone us-central1-a --count 3 --machine-type t2d-standard-1 --network-link global/networks/default --image-family debian-11 --disk-size-gb 10 --disk-type pd-standard --boot-disk-auto-delete True --boot-disk-boot True --external-ip ephemeral --tags http-server https-server --create-disk "auto-delete=yes,boot=yes,device-name=instance-1,image=projects/debian-cloud/global/images/debian-11-bullseye-v20230206,mode=rw,size=10,type=projects/falra-368206/zones/us-central1-a/diskTypes/pd-standard" --no-shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring --reservation-affinity any
gcloud projects add-iam-policy-binding  falra-368206 --role roles/compute.instanceAdmin --member 225040004642-compute@developer.gserviceaccount.com

python3 create_gcp_vms.py --project-id debian-cloud --zone us-central1-a --count 3
