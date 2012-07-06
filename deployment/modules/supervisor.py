from os.path import join as pjoin, isdir
from fabric.api import env, prefix, settings, sudo, hide
from fabric.colors import yellow, red
from utils import (cget, local_files_dir, show, upload_template_with_perms,
    cset, create_target_directories, upload_templated_folder_with_perms)


def configure():
    """Upload supervisor configuration files."""
    user = cget('user')
    # settings directories
    sdir = cset('supervisor_dir', pjoin(cget('service_dir'), 'supervisor'))
    slogdir = cset('supervisor_log_dir', pjoin(cget('log_dir'), 'supervisor'))
    cset("supervisor_process_base", cget('project_name').replace('-', '_'))
    cset("supervisor_process_id",
        '%s%s' % (cget('supervisor_process_base'), '_supervisor'))
    # create all dirs and log dirs
    dirs = ['', 'config', cget('project_name')]
    dirs = [pjoin(sdir, l) for l in dirs]
    log_dirs = ['', cget('project_name'), 'child_auto', 'solr']
    log_dirs = [pjoin(slogdir, l) for l in log_dirs]
    create_target_directories(dirs + log_dirs, "700", user)

    context = dict(env["ctx"])
    local_dir = local_files_dir("supervisor")
    dest_dir = pjoin(sdir, 'config')

    confs = cget("supervisor_files")
    show(yellow("Uploading service configuration files: %s." % confs))
    for name in confs:
        source = pjoin(local_dir, name)
        destination = pjoin(dest_dir, name)
        if isdir(source):
            upload_templated_folder_with_perms(source, local_dir, dest_dir,
                context, mode="644", directories_mode="700")
        else:
            upload_template_with_perms(
                source, destination, context, mode="644")

    scripts = ['supervisorctl.sh', 'supervisord.sh']
    for script_name in scripts:
        source = pjoin(cget("local_root"), 'deployment', 'scripts', script_name)
        destination = pjoin(cget("script_dir"), script_name)
        upload_template_with_perms(source, destination, context, mode="755")


def run_supevisordctl(command):
    """Start supervisor process."""
    conf = pjoin(cget('service_dir'), 'supervisor', 'config',
        'supervisord.conf')
    show(yellow("Running supervisorctrl: %s." % command))
    return sudo('supervisorctl --configuration="%s" %s' % (conf, command))


def start_supervisor():
    """Start supervisor process."""
    conf = pjoin(cget('service_dir'), 'supervisor', 'config',
        'supervisord.conf')
    pname = cget('supervisor_process_id')
    show(yellow("Starting supervisor with id: %s." % pname))
    return sudo('supervisord --configuration="%s"' % conf)


def reload():
    """Start or restart supervisor process."""
    ve_dir = cget("virtualenv_dir")
    activate = pjoin(ve_dir, "bin", "activate")
    show(yellow("Reloading supervisor."))
    with prefix("source %s" % activate):
        with settings(hide("stderr", "stdout", "running"), warn_only=True):
            res = run_supevisordctl('reload')
            if res.return_code != 0:
                show(yellow("Supervisor unavailable, starting new process."))
                res = start_supervisor()
                if res.return_code != 0:
                    show(red("Error starting supervisor!."))


def shutdown():
    """Requests supervisor process and all controlled services shutdown."""
    ve_dir = cget("virtualenv_dir")
    activate = pjoin(ve_dir, "bin", "activate")
    show(yellow("Shutting supervisor down."))
    with prefix("source %s" % activate):
        with settings(hide("stderr", "stdout", "running"), warn_only=True):
            res = run_supevisordctl('shutdown all')
            if res.return_code != 2:
                msg = "Could not shutdown supervisor, process does not exists."
                show(yellow(msg))
