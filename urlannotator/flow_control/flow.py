from celery import task


@task
def logging_task(name, *args, **kwargs):
    import logging
    log = logging.getLogger('EventLogging')
    log.debug("Got event: %s(%s, %s)", name, args, kwargs)


@task
def test_task(file_name):
    print file_name


FLOW_DEFINITIONS = [
    ('TestEvent', test_task),
    ('LogEvent', logging_task)
    ]
