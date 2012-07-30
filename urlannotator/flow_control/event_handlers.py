from celery import task


@task
def test_task(fname, content):
    with open(fname, 'w') as f:
        f.write(content)

FLOW_DEFINITIONS = [
    (r'^TestEvent$', test_task),
]
