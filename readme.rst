=============
URL Annotator
=============
<LAST_MODIFIFED>


Source/How to get it
====================
From github:

    git clone git@github.com:10clouds/urlannotator.git

What's new
==========
<WHATSNEW>

How it works
============
<HOWITWORKS>

Setup
=====
Required libraries:
-------------------
- Django>=1.4
- python-memcached
- South
- django-pipeline>=1.2
- ipdb
- ipython
- django-social-auth
- python-odesk
- bootstrap
- docutils
- validictory
- 10clouds/common
- django-celery
- boto
- numpy
- nltk
- django-tastypie

(See deployment/files/requirements/base.txt)

Basic setup:
------------
On local machine:

- Install easy_install

	sudo apt-get install python-setuptools python-dev build-essential

- Install pip

	easy_install pip

- Install virtualenv

	pip install virtualenv

- Pull repository to local filesystem

	git clone https://github.com/10clouds/urlannotator.git

- Create virtualenv

	virtualenv .env

- Activate virtualenv

	source .env/bin/access

- Install basic requirements

	sudo pip install -r urlannotator/deployment/files/requirements/base.txt

- Create database

    cd urlannotator

    ./manage.py syncdb

    ./manage.py migrate

- Install less (>=1.3.0)

    sudo apt-get install less

    - If your distribution's repository has outdated version of less (<1.3.0)

        sudo apt-get install npm

        - If your distribution's repository has outdated version of npm (<1.0.0), try compiling it npm from sources
        - Otherwise (npm>=1.0.0)

            sudo npm -g install less

- Run RabbitMQ if not running

    sudo rabbitmq-server -detached

- Run celery worker

    ./manage.py celery worker

On remote machine:

- Follow steps from local machine setup up to the point ``Install basic requirements``
- Install development requirements

	sudo pip install -r urlannotator/deployment/files/requirements/devel.txt

- Configure settings template at deployment/files/django/settings_template.py
- Create local settings file at deployment/files/django/local.py
- Configure deploy configuration at deployment/target_defs
- (First time) Setup and deploy to remote host:

	cd urlannotator/deployment

	fab deploy:conf_file="target_defs/<your_conf_file>.txt",setup_environment=True -H <host> -u <user>

- (Consequent deploys) Deploy to remote host:

    cd urlannotator/deployment

    fab deploy:conf_file="target_defs/<your_conf_file>.txt",requirements=False -H <host> -u <user>

DB setup:
---------
<DB_SETUP>

Cron setup:
-----------
<CRON_SETUP>

`More about DB setup <https://github.com/10clouds/urlannotator/blob/master/docs/dbsetup>`_
==========================================================================================

`More about Cron setup <https://github.com/10clouds/urlannotator/blob/master/docs/cronsetup>`_
==============================================================================================


Support
=======
<SUPPORT>
