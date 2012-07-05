from os.path import join as pjoin, isdir
from fabric.api import sudo, settings, env, hide
from fabric.colors import yellow
from modules.utils import (PROPER_SUDO_PREFIX as SUDO_PREFIX, show,
    cget, local_files_dir, upload_templated_folder_with_perms,
    upload_template_with_perms)


def configure():
    """Uploads postgresql configuration files."""
    context = dict(env["ctx"])
    local_dir = local_files_dir("postgresql")
    dest_dir = "/etc/postgresql"
    confs = cget("postgresql_files") or [local_dir]
    show(yellow("Uploading postgresql configuration files: %s." % confs))
    for name in confs:
        source = pjoin(local_dir, name)
        destination = pjoin(dest_dir, name)
        if isdir(source):
            upload_templated_folder_with_perms(source, local_dir, dest_dir,
                context, mode="644", directories_mode="700")
        else:
            upload_template_with_perms(
                source, destination, context, mode="644")


def reload():
    """Starts or restarts nginx."""
    with settings(hide("stderr"), sudo_prefix=SUDO_PREFIX):
        return sudo("service postgresql reload")
