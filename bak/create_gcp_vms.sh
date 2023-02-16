python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 create_gcp_vms.py --count 5 --firewall-rules http-server https-server
