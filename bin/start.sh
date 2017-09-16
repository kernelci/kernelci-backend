#!/bin/sh

# Starts
# - celery worker and beat
# - tornado server

celery worker -Ofair --without-gossip --autoscale=4,1 --logfile=/var/log/celery/%h%I.log --loglevel=INFO --app=taskqueue 
&& celery beat --loglevel=INFO --schedule /var/run/celery/kernelci-beat.db --app=taskqueue"
&& server.py
