from tastypie.resources import ModelResource
from django.conf.urls import url
import urllib
from celery.result import AsyncResult
import random

from urlannotator.classification.classifiers import SimpleClassifier
from urlannotator.main.models import Job, Worker, Sample
from urlannotator.main.factories import SampleFactory


class JobResource(ModelResource):
    class Meta:
        queryset = Job.objects.all()
        resource_name = 'job'
        list_allowed_methods = ['get']

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classify/$'
                % self._meta.resource_name,
                self.wrap_view('classify'), name='api_classify'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classify/'
                '(?P<task_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('classify_result'), name='api_classify_result'),
        ]

    def classify(self, request, **kwargs):
        """
            Initiates classification on passed url using classifier
            associated with job. Returns task id on success.
        """
        self.method_check(request, allowed=['get'])
        if 'url' not in request.GET:
            return self.create_response(request, {'error': 'Wrong url.'})

        try:
            job = Job.objects.get(id=kwargs['job_id'])
        except Job.DoesNotExist:
            return self.create_response(request, {'error': 'Wrong job.'})

        url = urllib.unquote_plus(request.GET['url'])
        w = Worker()
        w.save()

        task = SampleFactory().new_sample(job, w, url)

        return self.create_response(request, {'task_id': task.id})

    def classify_result(self, request, **kwargs):
        """
            Checks result of classification task initiated by user.
            On success, returns label given by the classificator
        """
        self.method_check(request, allowed=['get'])
        try:
            job = Job.objects.get(id=kwargs['job_id'])
        except Job.DoesNotExist:
            return self.create_response(request, {'error': 'Wrong job.'})

        if 'task_id' not in kwargs:
            return self.create_response(request, {'error': 'Wrong task id.'})

        if 'url' not in request.GET:
            return self.create_response(request, {'error': 'Wrong url.'})

        task = AsyncResult(id=kwargs['task_id'])
        resp = {'state': task.state}

        if task.ready():
            url = urllib.unquote_plus(request.GET['url'])
            Sample.objects.filter(url=url, label='').\
                update(label=random.choice(['Yes', 'No']))
            s = Sample.objects.filter(url=url)[0]
            sc = SimpleClassifier()
            sc.train(Sample.objects.filter(job=job))
            resp['outputLabel'] = sc.classify(s)
            resp['outputMulti'] = sc.classify_with_info(s)
        return self.create_response(request, resp)
