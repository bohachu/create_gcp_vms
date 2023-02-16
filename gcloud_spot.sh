#!/bin/bash

for i in {1..15}; do
    gcloud compute instances create "vm-${i}" \
        --boot-disk-size=10 \
        --boot-disk-type=pd-standard \
        --zone=us-central1-a \
        --preemptible &
done
