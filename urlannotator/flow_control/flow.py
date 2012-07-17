from celery import task


@task
def logging_task(name, *args, **kwargs):
    import logging
    log = logging.getLogger('EventLogging')
    print "logggig"
    log.debug("Got event: %s(%s, %s)", name, args, kwargs)


@task
def test_task(fname, content):
    with open(fname, 'w') as f:
        f.write(content)


FLOW_DEFINITIONS = [
    (r'TestEvent', test_task),
    (r'.*', logging_task)
    ]
