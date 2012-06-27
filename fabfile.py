from fabric import colors, api
from fabric import operations
from fabric.contrib.project import upload_project
import os


PROJECT_NAME = 'urlannotator'
PROJECT_ROOT = '/home/urlannotator.%s/urlannotator/'
DJANGO_ROOT = '%sapp' % PROJECT_ROOT
VIRTUAL_ENV = '. %sbin/activate' % PROJECT_ROOT
YUI_LOCATION = '%sbin/yuicompressor-2.4.7.jar' % DJANGO_ROOT
HOST = 'ubuntu@10.0.2.15'  # change to actual host

DEVEL = 'urlannotator.settings.devel'
STABLE = 'urlannotator.settings.stable'


def provision():

    # we are asking for all necessery data upfront so that we can go to grab a coffee or a fast 1v1 while it's installing
    version = operations.prompt('Please specify target version stable or devel: ', validate=r'^(stable|devel)$')
    db = operations.prompt('Please specify database engine [mysql|postgresql]: ', validate=r'^(mysql|postgresql)$')

    db_password = '10clouds'
    db_user = "%s_%s" % (PROJECT_NAME, version,)
    system_user = "%s.%s" % (PROJECT_NAME, version,)
    project_root = PROJECT_ROOT % version
    local_project_dir = os.path.abspath(os.path.dirname(__file__))

    with api.settings(warn_only=True):
        api.sudo('mkdir ~/.ssh')
        operations.put('~/.ssh/id_rsa.pub', '~/.ssh/authorized_keys', use_sudo=True)

    api.sudo('apt-get update')

    # install base packages

    # installing core stuff for a web server
    api.sudo('apt-get install -q -y python-virtualenv subversion mercurial python-all-dev curl python-flup nginx supervisor git')

    # install database
    # TODO make it a seperate command
    if db == 'mysql':

        api.sudo('echo "mysql-server mysql-server/root_password password %s" | debconf-set-selections' % db_password)
        api.sudo('echo "mysql-server mysql-server/root_password_again password %s" | debconf-set-selections' % db_password)
        api.sudo('apt-get install -q -y mysql-client mysql-server')

        # create database and setup user
        api.sudo("echo \"CREATE USER '%s'@'localhost' IDENTIFIED BY '%s';\" | mysql --password=%s" % (db_user, db_password, db_password))
        api.sudo("echo \"GRANT ALL PRIVILEGES ON *.* TO '%s'@'localhost';\" | mysql --password=%s" % (db_user, db_password))
        api.sudo("echo \"CREATE DATABASE %s DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;\" | mysql --password=%s" % (db_user, db_password))

    elif db == 'postgresql':
        raise Exception('Not implemented')

    # setup user name and account
    # TODO make it a seperate command
    api.sudo('useradd %s -m' % system_user)
    api.sudo('mkdir /home/%s/.ssh' % system_user, user=system_user)
    operations.put('~/.ssh/id_rsa.pub', '/home/%s/.ssh/authorized_keys' % system_user, use_sudo=True)

    # setup base directory structure
    # /home/urlannotator.version/log
    # /home/urlannotator.version/urlannotator

    api.sudo('mkdir -p %slog' % (project_root), user=system_user)
    api.sudo('mkdir -p %sapp' % (project_root), user=system_user)

    # setting up virtualenv
    api.sudo('virtualenv --no-site-packages %s' % (project_root), user=system_user)
    # TODO fetch required libraries for virtualenv

    # upload local version of app to remote server, you will still have to setup remote server auth keys
    # hackish solution but besides changing upload_projects code I dont see how to solve the problems of permissions
    api.sudo('chown -R %s:%s /home/%s/' % ('ubuntu', 'ubuntu', system_user))
    with api.cd(project_root):
        upload_project(local_project_dir, project_root + "app")

    api.sudo('chown -R %s:%s /home/%s/' % (system_user, system_user, system_user))

    # TODO setup requirements
    # TODO setup nginx config
    # TODO setup supervisor config
    # TODO restart nginx and supervisor
    pass


def show(msg, *args):
    print colors.cyan('==>', bold=True), msg % args


def update():
    show(colors.blue('updating %s repository' % PROJECT_NAME))
    with api.cd(PROJECT_ROOT):
        api.run('git stash')
        api.run('git pull --rebase')
        api.run('git diff')


def collectstatic(settings):
    show(colors.blue('collecting static files'))
    with api.prefix(VIRTUAL_ENV):
        with api.cd(DJANGO_ROOT):
            with api.settings(warn_only=True):
                api.run('mkdir collected_static')
            api.run('./manage.py collectstatic --noinput --settings=%s' % settings)


def migrate(settings):
    show(colors.blue('running migration scripts'))
    with api.prefix(VIRTUAL_ENV):
        with api.cd(DJANGO_ROOT):
            api.run('./manage.py migrate --settings=%s' % settings)


def supervisor(service, action):
    show(colors.blue('running "%s" for %s daemon services'), service, action)
    with api.settings(warn_only=True):
        api.run('sudo supervisorctl %s %s' % (action, service))


def service(service, action):
    show(colors.blue('running "%s" for %s daemon services'), service, action)
    with api.settings(warn_only=True):
        api.run('sudo /etc/init.d/%s %s' % (service, action,))


def install_requirements():
    show(colors.blue('updating %s repository' % PROJECT_NAME))
    with api.cd(PROJECT_ROOT):
        api.run('pip install -r requirements.txt')
        api.run('pip install -r requirements-server.txt')


def deploy():
    update()
    collectstatic(DEVEL)
    supervisor('devel', 'restart')
    service('nginx', 'reload')


def stop():
    supervisor('devel', 'stop')


def start():
    supervisor('devel', 'start')


def restart():
    supervisor('devel', 'restart')
