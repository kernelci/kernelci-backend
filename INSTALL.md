# KernelCi Backend Ansible installation process

Documentation of the Kernelci backend installation process

## KernelCI architecture overview

The architecture of kernelCI is split into three main components:
* Build system
* Frontend
* Backend

For more information on the architecture please visit: http://wiki.kernelci.org/

## Prerequisites

Two machines:
* The host machine which will run the ansible scripts to remotely install the back end onto the target machine.
	* Host configuration prerequisites
		* Git tools
		* Ansible >= 2.0: http://docs.ansible.com/ansible/latest/intro_installation.html
* The target machine where the kernelci infrastructure (front and back end) will be deployed
	* Target configuration prerequisites
		* Supported OS: Debian (Jessie and after), Centos >= 7
		* ssh root access to the server
		* Python >= 2.7.12

* Ansible need to have a way to be root either with direct root connect or either with user+sudo/su, you need to choose which way will be used.
	* For direct root access:
		* add ansible_ssh_user=root after serverhostname in hosts
	* For user+sudo
		* add ansible_ssh_user=user become_method=sudo after serverhostname in hosts
	* More informations on http://docs.ansible.com/ansible/latest/become.html

## Installing

### Install order
* You need to install the [backend first](http://github.com/kernelci/kernelci-backend-config/)
* Then you need to generate tokens for frontend and set them in secrets.yml
* Then install the [frontend](http://github.com/kernelci/kernelci-frontend-config/)

### Get the source code
```
For Deploying kernelci-backend
git clone https://github.com/kernelci/kernelci-backend-config.git
```

### Configure Host
* The server running the instance is named TARGET_NAME in the rest of the document
* You need to choose the FQDN used for calling both the frontend and backend; one FQDN for each, named FQDN_BACKEND and FQDN_FRONTEND in the rest of the document.
  These FQDN must be set in the hostname variable. Ddefault from group_vars/all is kernelci-frontend/kernelci-backend
  This name could be different from TARGET_NAME.
* Name example:
    * TARGET_NAME: server.mydomain.local
    * FQDN_FRONTEND: frontend.mydomain.local
    * FQDN_BACKEND: api.mydomain.local

	* Example:
	In host_vars/TARGET_NAME
	```
	hostname: FQDN_BACKEND
	```

* then add the choosen TARGET_NAME in the hosts file
	* Example:
```
[dev]
#this machine will be managed directly via root
TARGET_NAME ansible_ssh_user=root
[rec]
#this machine will be managed via the user admin becoming root via "su"
TARGET_NAME ansible_ssh_user=admin become_method=su
[prod]
#this machine will be managed via the user admin using sudo
TARGET_NAME ansible_ssh_user=admin become_method=sudo
```

### Create secrets.yml file
In order to run the entire configuration, some "secrets" are necessary.
Put them in a YAML file, and pass it to Ansible as:

    -e "@/path/to/file/secrets.yml"

To skip the secrets taks, just pass:

    --skip-tags=secrets

#### Secret Keys


The secret keys that have to be defined are:

* master_key: The password used for generating tokens before any admin token was created (See Manual tasks below).
* info_email: email address to be displayed for contact informations
* ssl_stapling_resolver: (optionnal)


Other non-secrets variable might need to be defined, please look at the `templates` directories.

### Run Ansible
```
$ cd <kernelci-backend-diretory>
$ ansible-playbook -i hosts site.yml -e "@../secrets.yml" -l <$TARGET_NAME> 
```

This will deploy the kernel-ci backend code into `/srv/$hostname`,
intall all dependencies and set up an nginx host called `$hostname`.

By default an S3-backup shell script and firewall rules via `ufw` will be
installed as well. Skip them with:

  --skip-tags=backup,firewall

### Requirements

Non exhaustive list of requirements is in the 'requirements.txt' file: those
need to be installed via pip.
For production, requirements.txt is sufficient. For development purpose, requirements-dev.txt
will add extra package for testing.
For the moment ansible does not handle this requirements-dev.txt.

### Token Management
- - - - 
Once the kernelCI backend is up and running, you need to create several tokens for inter process communication.

#### Admin token
The first token to create is the admin token. This token will be used for managing the whole KernelCI backend database.\
Make sure to write it down somewhere and not forget it.

The following example shows how to send a request to create an admin token.
```
$ curl -XPOST -H "Content-Type: application/json" -H "Authorization: MASTER_KEY" "BACKEND_URL/token" -d '{"email": "ADMIN_EMAIL", "username": "ADMIN_USERNAME", "admin": 1}'

```
Response:
```{"code":201,"result":[{"token":"ADMIN_TOKEN"}]}```\
Note that:
* MASTER_KEY and BACKEND_URL must replaced by the values specified in the secrets.yml file used by ansible.
* ADMIN_EMAIL and ADMIN_USERNAME must be replaced by the email and username for whom this token is created.
* ADMIN_TOKEN in the response will be the actual token created for the administrator.

#### KernelCI Frontend token
Second token to create is the KernelCI Frontend token. This token will allow the KernelCI Frontend to fetch data through the backend API.

The following example shows how to send a request to create a KernelCI Frontend token.
```
$ curl -XPOST -H "Content-Type: application/json" -H "Authorization: ADMIN_TOKEN" "BACKEND_URL/token" -d '{"email": "FRONTEND_MAINTAINER_EMAIL", "username": "BASE_URL", "get": 1, "post": 1}'

```
Response:
```{"code":201,"result":[{"token":"FRONTEND_TOKEN_VALUE"}]}```\
Note that:
* ADMIN_TOKEN must be replaced by the value of the admin token returned in the previous step (Admin token).
* BACKEND_URL must replaced by the values specified in the secrets.yml file used by ansible. It corresponds to the URL where KernelCI backend API is available
* ADMIN_EMAIL and ADMIN_USERNAME must be replaced by the email and username for whom this token is created.
* FRONTEND_TOKEN_VALUE in the response will be the actual token created for the KernelCI Frontend instance.

*Important steps once the token is created:*
* Note the FRONTEND_TOKEN_VALUE
* On the machine running the KernelCI Frontend services:
    * Edit the file /etc/linaro/kernelci-frontend.cfg
    * Add (or replace) the line ```BACKEND_TOKEN = ''``` and write FRONTEND_TOKEN_VALUE between the quotes
        * Example: ```BACKEND_TOKEN = 'de41df12-4s35-a547-b597-cebef80ae5ef'```
        * Where ```de41df12-4s35-a547-b597-cebef80ae5ef``` is the FRONTEND_TOKEN_VALUE returned by the curl command.

#### LAVA Lab callback token
To allow LAVA labs to submit results to your KernelCI instance, you need to genereate one token per LAVA lab.

The following example shows how to send a request to create a LAVA Lab token.

```
$ curl -XPOST -H "Content-Type: application/json" -H "Authorization: ADMIN_TOKEN" "BACKEND_URL/lab" -d '{"name": "LAB_NAME", "contact": {"name": "CONTACT_NAME", "surname": "CONTACT_SURNAME", "email": "CONTACT_MAIL"}}'
```
Response:
```{"code":201,"result":[{"_id":{"$oid":"59de2100708a590152c2a5c7"},"token":"LAB_TOKEN_VALUE","name":"LAB_NAME"}]}```\
Note that:
* ADMIN_TOKEN must be replaced by the value of the admin token returned in the previous step (Admin token).
* BACKEND_URL must replaced by the values specified in the secrets.yml file used by ansible. It corresponds to the URL where KernelCI backend API is available.
* LAB_NAME  must be replaced by the lab name for which the token is created
* CONTACT_NAME, CONTACT_SURNAME and CONTACT_MAIL must be replaced by the email and username for whom this token is created.
* LAB_TOKEN_VALUE in the response will be the actual token created for the KernelCI Frontend instance.
