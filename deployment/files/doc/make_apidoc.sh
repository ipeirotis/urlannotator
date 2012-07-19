#!/bin/bash
#
# Script for generating automated documentation using apidoc
#

echo "Generating apidoc"

. %(virtualenv_dir)s/bin/activate

# sphinx-apidoc -o <output_dir> <module_path> -H <project_name> [excluded_app1 [...]]
sphinx-apidoc -o %(doc_dir)s/source/apidoc/app %(manage_py_dir)s/%(django_project_name)s -H %(project_display_name)s %(autodoc_excluded_apps)s
sphinx-apidoc -o %(doc_dir)s/source/apidoc/deployment %(project_dir)s/code/deployment -H Deployment
sphinx-build %(doc_dir)s/source %(doc_dir)s/build
