# KernelCi Backend Ansible installation process

Documentation of the Kernelci backend installation process

## KernelCI architecture overview

The architecture of kernelCI is split into three main components:
* Build system
* Frontend
* Backend

For more information on the architecture please visit:  http://wiki.kernelci.org/

## Prerequisites

Two machines:
* The host machine which will run the ansible scripts to remotely install the back end onto the target machine.
	* Host configuration prerequisites
		* Git tools
		* Ansible >= 2.0: http://docs.ansible.com/ansible/latest/intro_installation.html
* The target machine where the kernelci infrastructure (front and back end) will be deployed
	* Target configuration prerequisites  
		* Supported OS: Debian (Jessie)
		* ssh root access to the server
		* Python >= 2.7.12

## Installing

### Get the source code
```
$ git clone https://github.com/kernelci/kernelci-backend-config.git
```

### Configure Host
Edit /etc/hosts - add new line:
```
<TARGET_IP> <TARGET_NAME>
```

### Create secrets.yml file
In order to run the entire configuration, some "secrets" are necessary.
Put them in a YAML file, and pass it to Ansible as:

    -e "@/path/to/file/secrets.yml"

To skip the secrets taks, just pass:

    --skip-tags=secrets

#### Secret Keys


The secret keys that have to be defined are:

* backend_url
* base_url
* backend_token
* secret_key
* info_email
* ssl_stapling_resolver
* google_analytics


The `secret_key` value should be set to a random string, it is used internally
by Flask.

Other non-secrets variable might need to be defined, please look at the `templates` directories.

### Run Ansible
```
$ cd <kernelci-backend-diretory>
$ ansible-playbook -i hosts site.yml -e "@../secrets.yml" -l <$TARGET_NAME> 
```