from tastypie.resources import ModelResource
from django.conf.urls import url
import urllib

from urlannotator.main.models import Job, Worker, ClassifiedSample
from urlannotator.flow_control import send_event


class JobResource(ModelResource):
    """ Resource allowing API access to Jobs
    """
    class Meta:
        queryset = Job.objects.all()
        resource_name = 'job'
        list_allowed_methods = ['get']

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classify/$'
                % self._meta.resource_name,
                self.wrap_view('classify'), name='api_classify'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classify/status/$'
                % self._meta.resource_name,
                self.wrap_view('get_classify_status'),
                name='api_classify_status'),
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

        # Create classified sample and raise event to create a new sample.
        # A classified sample monitor will update classified_sample.sample
        # as soon as a sample with given url and job is created
        classified_sample = ClassifiedSample(job=job, url=url, label='')
        classified_sample.save()
        send_event('EventNewRawSample', job.id, w.id, url)

        return self.create_response(request,
            {'request_id': classified_sample.id})

    def get_classify_status(self, request, **kwargs):
        """
            Checks result of classification task initiated by user.
            On success, returns label given by the classificator.
        """
        self.method_check(request, allowed=['get'])
        try:
            job = Job.objects.get(id=kwargs['job_id'])
        except Job.DoesNotExist:
            return self.create_response(request, {'error': 'Wrong job.'})

        if 'request' not in request.GET:
            return self.create_response(request,
                {'error': 'Wrong request id.'})

        try:
            request_id = int(request.GET['request'])
        except:
            return self.create_response(request,
                {'error': 'Wrong request id.'})

        try:
            classified_sample = ClassifiedSample.objects.get(job=job,
                id=request_id)
        except ClassifiedSample.DoesNotExist:
            return self.create_response(request,
                {'error': 'Wrong request id.'})

        resp = {}
        status = 'PENDING'
        if classified_sample.sample and classified_sample.sample.label:
            status = 'SUCCESS'
            resp['outputLabel'] = classified_sample.sample.label

        resp['status'] = status
        return self.create_response(request, resp)
