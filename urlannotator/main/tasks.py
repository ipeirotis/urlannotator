from celery import task


@task()
def add(x, y):
    return x + y


@task()
def html_content_extraction(url):
    pass
