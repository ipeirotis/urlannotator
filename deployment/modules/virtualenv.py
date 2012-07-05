from os.path import join as pjoin

from fabric.contrib.files import exists
from fabric.colors import yellow, green
from fabric.api import hide, settings, sudo, prefix
from utils import (show, dir_exists, PROPER_SUDO_PREFIX as SUDO_PREFIX, cget,
    install_without_prompt, remote_files_dir)


def update_virtualenv():
    """Updates virtual Python environment."""
    ve_dir = cget("virtualenv_dir")
    activate = pjoin(ve_dir, "bin", "activate")
    user = cget("user")
    cache = cget("pip_cache")

    show(yellow("Updating Python virtual environment."))
    show(green("Be patient. It may take a while."))

    for req in cget('pip_requirements'):
        requirements = pjoin(remote_files_dir('requirements'), req)
        show(yellow("Processing requirements file: %s" % requirements))
        with settings(warn_only=True, sudo_prefix=SUDO_PREFIX):
            with prefix("source %s" % activate):
                sudo("pip install --no-input --download-cache=%s"
                    " --requirement %s --log=/tmp/pip.log" % (
                        cache, requirements), user=user)


def create_virtualenv():
    """Creates the virtualenv."""
    user = cget("user")
    ve_dir = cget("virtualenv_dir")
    bin_path = pjoin(ve_dir, "bin")
    if not dir_exists(bin_path) or not exists(pjoin(bin_path, "activate")):
        show(yellow("Setting up new Virtualenv in: %s"), ve_dir)
        with settings(hide("stdout", "running"), sudo_prefix=SUDO_PREFIX):
            sudo("virtualenv --distribute %s" % ve_dir, user=user)


def setup_virtualenv():
    """Installs virtualenv."""
    install_without_prompt('python-virtualenv', 'python virtual environment')
