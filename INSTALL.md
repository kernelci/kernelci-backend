# KernelCI Backend Ansible installation process

Documentation of the KernelCI backend installation process

## KernelCI architecture overview

The architecture of KernelCI is split into three main components:
* Build system
* Frontend
* Backend

For more information on the architecture please visit: http://wiki.kernelci.org/

## Prerequisites

Two machines:

* The host machine which will run the ansible scripts to remotely install the backend onto the target machine.
	* Host configuration prerequisites
		* Git tools
		* Ansible >= 2.0: http://docs.ansible.com/ansible/latest/intro_installation.html

* The target machine where the KernelCI infrastructure (front and back end) will be deployed
	* Target configuration prerequisites
		* Supported OS: Debian Buster, CentOS >= 7
		* ssh root access, at least for the host machine from where you'll be running ansible
		* Python >= 2.7.12

* Ansible need to have a way to be root in the target machine, either with direct root connect or with user+sudo/su, you need to choose which way will be used.
	* For direct root access:
		* add `ansible_ssh_user=root` after serverhostname in the hosts file
	* For user+sudo
		* add `ansible_ssh_user=user become_method=sudo` after serverhostname in the hosts file
	* More information on http://docs.ansible.com/ansible/latest/become.html

## Installing

### Install order
* You need to install the [backend first](http://github.com/kernelci/kernelci-backend-config/)
* Then you need to generate tokens for frontend and set them in secrets.yml
* Then install the [frontend](http://github.com/kernelci/kernelci-frontend-config/)

### Get the ansible playbook

If you didn't clone this repository yet, you need to do it for running the ansible playbook installing the backend:

```
git clone https://github.com/kernelci/kernelci-backend-config.git
```

### Configuration
* The server running the instance is named TARGET_NAME in the rest of the document
* You need to choose the FQDN used for calling both the frontend and backend; one FQDN for each, named FQDN_BACKEND and FQDN_FRONTEND in the rest of the document.
  These FQDN must be set in the hostname variable. The default in `group_vars/all` is kernelci-frontend/kernelci-backend
  This name could be different from TARGET_NAME.
* Naming example:
    * TARGET_NAME: server.mydomain.local
    * FQDN_FRONTEND: frontend.mydomain.local
    * FQDN_BACKEND: api.mydomain.local
    * FQDN_STORAGE: storage.mydomain.local

The storage service is installed alongside the backend so you don't need to run a different playbook for this. This service is only a directory browseable where the backend will host the logs and build results.  However you should add a cname to the server hosting the backend using the FQDN given to the storage.

You need to modify or add the following files:

* `group_vars/all` :
Replace hostname and nickname for something else if you don't want to use kernelci-backend.
Change the role to "staging" instead of "production" if you're installing locally for testing or development.
Replace kci_storage_fqdn with the name you'll be using for the storage.

* `hosts`:
Add the TARGET_MACHINE and configure how to ansible should connect, for example if your machine
is named backend.mydomain.local with IP 10.0.17.2 and you connect directly as root (using a ssh key),
your should add:

```
[local]
TARGET_MACHINE ansible_ssh_port=22 ansible_ssh_host=10.0.17.2 ansible_ssh_user=root
```

If the user is not root and should use "su" to become root, use the parameter `become_method=su`, if it should use "sudo" instead, use `become_method=sudo`

* `host_vars/TARGET_NAME` this is a file that you must create

For example, you can create the file  `host_vars/myserver.mydomain.local` with the following content:

```
hostname: backend.mydomain.local
role: staging
```


### Create secrets.yml file
In order to run the entire configuration, some "secrets" are necessary.
Use the file `templates/secrets.yaml` as an example and provide it to ansible:

    -e "@/path/to/file/secrets.yml"

To skip the secrets tasks, just pass:

    --skip-tags=secrets


The only secret key that have to be defined for a local installation for testing ot development is:

* master_key: The password used for generating tokens before any admin token was created (See Manual tasks below).

Other non-secrets variable might need to be defined, please look at the comments in the file.

### Run Ansible

From the root directory of this repository run:

```
$ ansible-playbook -i hosts site.yml -e "@../secrets.yml" -l <$TARGET_NAME>
```

This will deploy the [KernelCI backend code](https://github.com/kernelci/kernelci-backend.git) into `/srv/$hostname`, install all dependencies and set up an nginx host called `$hostname`.

### Requirements

Non exhaustive list of requirements is in the 'requirements.txt' file: those
need to be installed via pip.
For production, requirements.txt is sufficient. For development purpose, requirements-dev.txt
will add extra package for testing.
For the moment ansible does not handle this requirements-dev.txt.

## Token Management

Once the KernelCI backend is up and running, you need to create several tokens for inter process communication.

### Admin token
The first token to create is the admin token. This token will be used for managing the whole KernelCI backend database. Make sure to write it down somewhere and not forget it.

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

### KernelCI Frontend token
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

Important steps once the token is created:

* Note the FRONTEND_TOKEN_VALUE
* On the machine running the KernelCI Frontend services:
    * Edit the file `/etc/kernelci/kernelci-frontend.cfg`
    * Add (or replace) the line ```BACKEND_TOKEN = ''``` and write FRONTEND_TOKEN_VALUE between the quotes
        * Example: ```BACKEND_TOKEN = 'de41df12-4s35-a547-b597-cebef80ae5ef'```
        * Where ```de41df12-4s35-a547-b597-cebef80ae5ef``` is the FRONTEND_TOKEN_VALUE returned by the curl command.


### LAVA Lab callback token
To allow LAVA labs to submit results to your KernelCI instance, you need to generate one token per LAVA lab.

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
