.. contents:: Table of Contents

=============
URL Annotator
=============
Last modified: September 18, 2012


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
- google-api-python-client
- posix-ipc
- 10clouds/tagasauris-api
- Pillow==1.7.7
- futures

(See deployment/files/requirements/base.txt)

Basic setup:
------------
On local machine:

- Install easy_install

	sudo apt-get install python-setuptools python-dev build-essential rabbitmq-server

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

- Install PyQt4:

    sudo apt-get install python-qt4

- Check your python-qt4 version:

    sudo apt-cache show python-qt4

- If your python-qt4 version is below 4.9.0:

    sudo apt-get install python-qt4-dev

    sudo apt-get install libqt4-dev

    Download and install SIP from http://www.riverbankcomputing.com/software/sip/download via command:

    cd /tmp && curl http://www.riverbankcomputing.com/static/Downloads/sip4/sip-4.13.3.tar.gz | tar -zxv && cd /tmp/sip-4.13.3 && python configure.py && sudo make && sudo make install

    Download and install python-qt4 from http://www.riverbankcomputing.com/software/pyqt/download via command:

    cd /tmp && curl http://www.riverbankcomputing.com/static/Downloads/PyQt4/PyQt-x11-gpl-4.9.4.tar.gz | tar -zxv && cd /tmp/PyQt-x11-gpl-4.9.4 && python configure.py && sudo make && sudo make install

- Link PyQt4 and sip.so into your virtual env

    ln -s /usr/lib/python2.7/dist-packages/PyQt4 .env/lib/python2.7/site-packages/PyQt4

    ln -s /usr/lib/python2.7/dist-packages/sip.so .env/lib/python2.7/site-packages/sip.so

- Create database

    cd urlannotator

    ./manage.py syncdb

    ./manage.py migrate

- Create Google Prediction credentials

    ./manage.py runserver

    visit http://127.0.0.1:8000/debug/prediction

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

- Follow steps from local machine setup up to the point ``Create Google Prediction credentials``
- Install development requirements

	pip install -r urlannotator/deployment/files/requirements/devel.txt

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
