KernelCi Backend Config
=======================

This is the Ansible configuration to deploy/setup the kernelci-backend
system at:

    https://github.com/kernelci/kernel-ci-backend

Requirements
############

Ansible >= 2.0

In order to run the entire configuration, some "secrets" are necessary.
Put them in a YAML file, and pass it to Ansible as:

    -e "@/path/to/file/secrets.yml"

To skip the secrets taks, just pass:

    --skip-tags=secrets

Secret Keys
-----------

The secret keys that have to be defined are:

* smtp_host
* smtp_user
* smtp_sender
* smtp_sender_desc
* smtp_password
* info_email
* s3_bucket_name
* s3_access_key
* s3_secret_key
* master_key
* zabbix_ip
* ssl_stapling_resolver

Other non-secrets variable might need to be defined, please look at the
`templates` directories.
