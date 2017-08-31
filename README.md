# swt-api

This repo sets up the API for the SWT react application.

## Installation instructions
The api can run as a standalone application, or as a docker container. Additionally, the jenkinsfile/dockerfile provide a fully automated deployment to aws' ecr/ecs

- install python > 3.6 on the vm

- clone the repo, setup virtual environment, and install requirements
```
$ git clone git@github.com:sbour/swt-api.git 
$ cd swt-api
$ pyenv venv
$ sudo pip install -r requirements.txt
```
- install modified flask_restiful_LC - it's not included in requirements.txt due to error installing with pip
```bash
$ git clone git@github.com:sbour/flask-restful_LC.git
$ cd flask-restful_LC
$ python3 setup.py install
```


- create ~/.vault_pass.txt password file
  ```bash
    $ echo $ANSIBLE_VAULT_PASS >> ~/.vault_pass.txt
  ```
- decrypt the correct config file for the environment
```bash
$ansible-vault decrypt --vault-password-file ~/.vault_pass.txt swt/config-stag.ini.vault
``` 

### for dev, start the server

```
$ python3 server.py
```

### In production, run the app with supervisor
- install supervisor on the vm
- add contents of supervisor_api.ini to /etc/supervisor/conf.d/swt-api.conf
```
$ sudo cp supervisor-api.ini /etc/supervisor/conf.d/swt-api.conf
```
- start supervisor
```bash
$ sudo supervisorctl reread
$ sudo supervisorctl reload
$ sudo supervisorctl start api

```


### Run app in a container in a vm:
- login to registry
```bash
$ docker login --username=<username> --password=<passwd>
```
- pull image from registry (tag should = latest)
```bash
$ docker pull <registry>/<namespace>:<tag> 

```
- run container:
```bash
docker run -itd --name swt-api2 --restart=always -p 5000:5000 registry/namespace:latest
```

### Run app in a container in ecs:
- create a cluster in ecs
- add a task with the container from ecr registry
The app will be available on the cluster's ec2 ip and the specified port 


### Proxy the requests
API requests can sent to a vm instance on port 80, and apache used as a reverse proxy:
- add mod_proxy to apache. Install all at once:
```bash
$ a2enmod
```
of install one by one:
```bash
$ sudo a2enmod proxy
$ sudo a2enmod proxy_http
$ sudo a2enmod proxy_balancer
$ sudo a2enmod lbmethod_byrequests

```

- edit /etc/apache2/sites-enabled/000-default.conf
```html
    <VirtualHost *:*>
        ProxyPreserveHost On
    
        # Servers to proxy the connection, or;
        # List of application servers:
        # Usage:
        # ProxyPass / http://[IP Addr.]:[port]/
        # ProxyPassReverse / http://[IP Addr.]:[port]/
        # Example: 
        ProxyPass / http://0.0.0.0:5000/
        ProxyPassReverse / http://0.0.0.0:5000/
    
        ServerName localhost
    </VirtualHost>
```


&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;


# Customizations
1. Exception handling
 - flask restful was modified in order to return my custom Exception class
in flask-restful/flask_restful/__init__.py :
 ```python
    headers = Headers()
    if isinstance(e, HTTPException):
        code = e.code
        default_data = {
            'message': getattr(e, 'description', http_status_message(code))
        }
        headers = e.get_response().headers
    else:
        """
        # Luis edited this code to
        Accept Custom Exception Classes
        """
        code = int(e.code)
        default_data = {
            'title': e.title,
            'status': False,
            "statusText": e.description
        }
    
        """
        code = 500
        default_data = {
            'message': http_status_message(code),
      }"""
```

# Tests
- discover any tests in test folder: (see setup.cfg for addiction params, such as coverage)
```bash
$ pytest
``` 
- run tests in .tox virtual environment)
```bash
$ tox
 ```  
run tests after recreating the .tox virtual environment
```bash
$tox --recreate
```
- runs the test command in setup.cfg
```bash 
$ python setup.py test
```  



## Develop the fse algorithm
* fse is in resources/fse/__init__.py
* don't forget to pull before pushing


# Customizations
1. Exception handling
 - flask restful was modified in order to return the my custom Exception class
 flask-restful/flask_restful/__init__.py
 ```python
    headers = Headers()
    if isinstance(e, HTTPException):
        code = e.code
        default_data = {
            'message': getattr(e, 'description', http_status_message(code))
        }
        headers = e.get_response().headers
    else:
        """
        # Luis edited this code to
        Accept Custom Exception Classes
        """
        code = int(e.code)
        default_data = {
            'title': e.title,
            'status': False,
            "statusText": e.description
        }
    
        """
        code = 500
        default_data = {
            'message': http_status_message(code),
      }"""
```

#Generate a data container for tests:

run a mysql container linking the host volume /dbdata with mysql's dir on the container
```
docker run --name dpcc_swt -v /dbdata:/var/lib/mysql -e MYSQL_ROOT_PASSWORD=passwd -d mysql:latest
```

run a temporary container to import the sql dump file into the mysql container. It will persist in the volume of the volume container
```
docker run -itd --link dpcc_swt:db --rm -v test/data/sql/DPCC_SWT_DEV_20170408/:/var/data -w /var/data mysql sh -c 'exec  mysql -h"$DB_PORT_3306_TCP_ADDR" -P"$DB_PORT_3306_TCP_PORT" -uroot -p"$DB_ENV_MYSQL_ROOT_PASSWORD" < all.sql'
```

remove the mysql container
```
docker rm -f dpcc_swt
```

mv /dbdata to current dir
```bash
mv /dbdata .
```

create dockerfile to create dbstore image with the data
```text
FROM python:3.6.1

RUN mkdir /var/lib/mysql

ADD /dbdata/ /var/lib/mysql

VOLUME /var/lib/mysql
```

build the dbstore image

```bash
docker build -t dbstore .
```

tag dbstore image and push
```bash
docker login -u <username> -p <password>
docker tag dbstore lfcunha/swt_api_test_data:latest
docker push lfcunha/swt_api_test_data:latest
```


# Jenkins + docker

- create db container
- import sql data using temp container
- use the configuration file config-test.ini (specifies mysql container as the mysql host)

- inside container: git clone and install my flask-restful
- commit the changes to the container: (change command if needed)
    sudo docker commit --change='CMD ["python3", "/opt/swt/swt-api/server.py"]' swt swt-api:<gitcommittag>

- docker tag swt-api:<gitcommittag> lfcunha/swt-py-api:latest
- docker push lfcunha/swt-py-api:latest
- send signal to server to pull container


run container (sharing ssh if need to use keys):
```bash
sudo docker run -itd -v ~/.ssh/:/ssh --restart=always -p 5000:5000 --name swt-api lfcunha/swt-py-api:latest
```

if running container locally, set up tunnel to rds
```bash
ssh -o ServerAliveInterval=60 -N -L 8065:stagdev.ceo3a2r3fyoz.us-east-1.rds.amazonaws.com:3306 ec2-user@54.172.75.68
(first add the bastion key)
```
# swt_api
