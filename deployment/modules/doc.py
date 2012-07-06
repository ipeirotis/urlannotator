from django.template.defaultfilters import slugify
from os.path import join as pjoin
from fabric.api import env, settings, sudo, hide
from fabric.colors import yellow
from utils import (cget, local_files_dir, show, upload_template_with_perms,
    create_target_directories, ensure_permissions, run_django_cmd, cset, run)


def configure():
    """Configures the doc module.

    Creates doc_dir and copies documentation sources there.
    Formats and uploads scripts for building the documentation.
    Finally, loads django-sphinxdoc project from a fixture.

    Project fixture can be found in deployment/files/doc/fixture.json.

    """
    # Add extra context variables used by sphinx-doc and apidoc
    excluded = cget('autodoc_excluded_apps')
    excluded = ' '.join(excluded) if excluded else ''
    cset("autodoc_excluded_apps", excluded, force=True)
    cset("project_display_name_slug", slugify(cget('project_display_name')))

    # Asure the doc folder exists
    user = cget('user')
    ddir = cget('doc_dir')
    source_doc_dir = pjoin(cget("project_dir"), "code", "doc")
    create_target_directories([ddir], "755", user)

    # Delete the content of the folder if exist
    with settings(hide("running", "stdout", "stderr")):
        output = sudo('ls -A {doc_dir}'.format(doc_dir=ddir))
        if len(output) > 0:
            sudo("rm -r {doc_dir}/*".format(doc_dir=ddir))

    # Copy files to doc dir
    with settings(hide("running", "stdout")):
        run("cp -r {source}/* {dest}".format(source=source_doc_dir, dest=ddir))
    ensure_permissions(ddir, user=user, group=user, recursive=True)

    context = dict(env["ctx"])

    # Upload formatted build script
    scripts = ['make_apidoc.sh']
    local_dir = local_files_dir("doc")
    show(yellow("Uploading doc scripts: {0}.".format(' '.join(scripts))))
    for script_name in scripts:
        source = pjoin(local_dir, script_name)
        destination = pjoin(cget("script_dir"), script_name)
        upload_template_with_perms(source, destination, context, mode="755")

    # Upload formatted conf.py file
    show(yellow("Uploading formatted conf.py file."))
    conf_file = "conf_formatted.py"
    source = pjoin(cget("local_root"), "doc", 'source', conf_file)
    destination = pjoin(ddir, 'source', conf_file)
    upload_template_with_perms(source, destination, context, mode="755")

    # Add Project to the database using formatted fixture and loaddata
    show(yellow("Adding django-sphinxdoc database models."))
    fixture_name = "fixture.json"
    source = pjoin(local_dir, fixture_name)
    destination = pjoin(ddir, fixture_name)
    upload_template_with_perms(source, destination, context, mode="755")
    run_django_cmd('loaddata', args=destination)


def build():
    """Creates the documentation files and adds them to the database.

    The first step is to create automatic module documentation using apidoc.

    Next the documentation is built and added to the database using
    updatedoc management command from django-sphinxdoc.

    See doc/readme.rst for more details.

    Apidoc generating script resides in deployment/files/doc/make_apidoc.sh.
    Note: This script is project-specific.

    """
    show(yellow("Bulding documentation"))
    apidoc_script = pjoin(cget("script_dir"), "make_apidoc.sh")
    with settings(hide("running", "stdout"), warn_only=True):
        run(apidoc_script)
    run_django_cmd('updatedoc',  args='-b ' + cget('project_display_name_slug'))
