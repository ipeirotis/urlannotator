from celery import task


@task
def test_task(fname, content):
    with open(fname, 'w') as f:
        f.write(content)


@task
def test_task_2(fname, content):
    with open(fname, 'w') as f:
        f.write(content[::-1])


FLOW_DEFINITIONS = [
    (r'^TestEvent$', test_task),
]
