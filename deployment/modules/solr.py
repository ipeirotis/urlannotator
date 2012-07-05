from os.path import join as pjoin, isdir
from fabric.api import sudo, settings, env
from fabric.colors import yellow
from modules.utils import (PROPER_SUDO_PREFIX as SUDO_PREFIX, show,
    cset, cget, local_files_dir, upload_templated_folder_with_perms,
    upload_template_with_perms, create_target_directories)


def provision(update=False):
    """Uploads an install script to /project_name/scripts and runs it.
    The script will not download solr if '/tmp/{project_name}/solr.zip' exists,
    nor it will attempt an install (eg. unpack and copy) if the following file
    exists: '{supervisor_dir}/solr/fabric_solr_install_success' (root of where
    solr is installed).

    Use update=True is as an override.
    """
    # upload the script to {project_dir}/scripts/setup_solr.sh
    user = cget("user")
    solr_dir = cset('solr_dir', pjoin(cget("service_dir"), 'solr'))

    script_name = "setup_solr.sh"
    source = pjoin(cget("local_root"), 'deployment', 'scripts', script_name)

    dest_scripts = cget("script_dir")
    create_target_directories([dest_scripts, solr_dir], "700", user)

    context = dict(env['ctx'])
    destination = pjoin(dest_scripts, script_name)
    upload_template_with_perms(source, destination, context, mode="644")

    # run the script
    show(yellow("Installing solr with update=%s." % update))
    with settings(sudo_prefix=SUDO_PREFIX, warn_only=True):
        script = destination
        # the script will copy files into: MTURK/solr
        ret = sudo("MTURK={home} && UPDATE={update} && . {script}".format(
            home=cget('service_dir'), script=script,
            update='true' if update else 'false'))
        if ret.return_code != 0:
            show(yellow("Error while installing sorl."))


def configure():
    """Uploads solr configuration files."""
    context = dict(env["ctx"])
    local_dir = local_files_dir("solr")
    dest_dir = pjoin(cget('service_dir'), 'solr')
    confs = cget("solr_files") or [local_dir]
    show(yellow("Uploading solr configuration files: %s." % confs))
    for name in confs:
        source = pjoin(local_dir, name)
        destination = pjoin(dest_dir, name)
        if isdir(source):
            upload_templated_folder_with_perms(source, local_dir, dest_dir,
                context, mode="644", directories_mode="700")
        else:
            upload_template_with_perms(
                source, destination, context, mode="644")
