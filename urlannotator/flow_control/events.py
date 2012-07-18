from django.conf import settings

from celery import task


@task
def test_task(fname, content):
    with open(fname, 'w') as f:
        f.write(content)


settings.FLOW_DEFINITIONS += [
    (r'TestEvent', test_task),
]
