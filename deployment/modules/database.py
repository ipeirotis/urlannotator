from fabric import colors
from fabric.api import sudo, task, hide, settings
from utils import (show, PROPER_SUDO_PREFIX as SUDO_PREFIX)


def call_psql(sql_command, database=None):
    with settings(hide("stderr"), sudo_prefix=SUDO_PREFIX):
        database = ' -d %s' % database if database is not None else ''
        return sudo('psql -tAc "%s"%s' % (sql_command, database),
            user="postgres")


@task
def create_user(dbuser, dbpass):
    "Create PostgreSQL user."
    show(colors.yellow("Creating PostgreSQL user: %s"), dbuser)
    sql_command = ("CREATE USER %s WITH CREATEDB NOCREATEUSER "
            "ENCRYPTED PASSWORD E\'%s\'" % (dbuser, dbpass))
    call_psql(sql_command)


@task
def create_database(dbname, owner):
    "Creates PostgreSQL DB with name and owner."
    show(colors.yellow("Creating PostgreSQL database: %s"), dbname)
    sql_command = ("CREATE DATABASE %s WITH OWNER %s" % (dbname, owner))
    call_psql(sql_command)


def ensure_language(dbname, lang):
    """Ensures language exists."""
    sql_command = """
    CREATE OR REPLACE FUNCTION create_language_{0}() RETURNS BOOLEAN AS \$\$
        CREATE LANGUAGE {0};
        SELECT TRUE;
    \$\$ LANGUAGE SQL;

    SELECT CASE WHEN NOT
        (
            SELECT  TRUE AS exists
            FROM    pg_language
            WHERE   lanname = '{0}'
            UNION
            SELECT  FALSE AS exists
            ORDER BY exists DESC
            LIMIT 1
        )
    THEN
        create_language_{0}()
    ELSE
        FALSE
    END AS {0}_created;

    DROP FUNCTION create_language_{0}();
    """.format(lang)
    show(colors.yellow("Ensuring PostgreSQL language exists: %s"), lang)
    call_psql(sql_command, database=dbname)


def check_user(dbuser):
    sql_command = "SELECT 1 FROM pg_roles WHERE rolname='%s';" % dbuser
    with settings(hide("stdout", "running")):
        result = call_psql(sql_command)
        return bool(result)


def ensure_user(dbuser, dbpass):
    "Checks whether PostgreSQL user exists, creates if not."
    if not check_user(dbuser):
        show("User %s does not exist in this instance", dbuser)
        create_user(dbuser, dbpass)


def check_database(dbname):
    sql_command = "SELECT 1 FROM pg_database WHERE datname='%s';" % dbname
    with settings(hide("stdout", "running")):
        result = call_psql(sql_command)
        return bool(result)


def ensure_database(dbname, owner):
    "Checks whether PostgreSQL database exists, creates if not."
    if not check_database(dbname):
        show("Database %s does not exist in this instance", dbname)
        create_database(dbname, owner)
