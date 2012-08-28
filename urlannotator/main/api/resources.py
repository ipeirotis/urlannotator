import json
import urllib

from django.conf.urls import url

from tastypie.resources import ModelResource

from urlannotator.main.models import (Job, Sample, Worker, LABEL_BROKEN,
    LABEL_YES, LABEL_NO)
from urlannotator.classification.models import ClassifiedSample
from urlannotator.crowdsourcing.models import SampleMapping, WorkerQualityVote

import logging
log = logging.getLogger(__name__)


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

        # Create classified sample and raise event to create a new sample.
        # A classified sample monitor will update classified_sample.sample
        # as soon as a sample with given url and job is created
        classified_sample = ClassifiedSample.objects.create_by_owner(
            job=job,
            url=url,
            label=''
        )

        return self.create_response(
            request,
            {'request_id': classified_sample.id}
        )

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
            return self.create_response(
                request,
                {'error': 'Wrong request id.'}
            )

        try:
            request_id = int(request.GET['request'])
        except:
            return self.create_response(
                request,
                {'error': 'Wrong request id.'}
            )

        try:
            classified_sample = ClassifiedSample.objects.get(
                job=job,
                id=request_id
            )
        except ClassifiedSample.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong request id.'}
            )

        resp = {}
        status = classified_sample.get_status()
        resp['status'] = status
        if classified_sample.is_successful():
            resp['outputLabel'] = classified_sample.label

        return self.create_response(request, resp)


class TagasaurisNotifyResource(ModelResource):
    """ Entry point for externally gathered samples.
    """

    notification_required = ['worker_id', 'results']

    def parse_notification(self, request):
        """
            Initiates classification on passed url using classifier
            associated with job. Returns task id on success.
        """

        data = json.loads(request.raw_post_data)

        self.method_check(request, allowed=['post'])
        for req in self.notification_required:
            if req not in data:
                return self.create_response(request,
                    {'error': 'Missing "%s" parameter.' % req})

        results = data['results']
        worker_id = data['worker_id']

        return worker_id, results


class SampleResource(TagasaurisNotifyResource):
    """ Entry point for externally gathered samples.
    """

    class Meta:
        resource_name = 'sample'
        list_allowed_methods = ['post']

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('add_from_tagasauris'),
                name='sample_add_from_tagasauris'),
        ]

    def add_from_tagasauris(self, request, **kwargs):
        """
            Initiates classification on passed url using classifier
            associated with job. Returns task id on success.
        """

        try:
            job = Job.objects.get(id=kwargs['job_id'])
        except Job.DoesNotExist:
            return self.create_response(request, {'error': 'Wrong job.'})

        worker_id, results = self.parse_notification(request)

        sample_ids = []
        for mediaobject_id, answers in results.iteritems():
            for answer in answers:
                for res in answer['results']:
                    sample = Sample.objects.create_by_worker(
                        job_id=job.id,
                        url=res['answer'],
                        label='',
                        source_val=worker_id
                    )
                    sample_ids.append(sample.id)

        return self.create_response(
            request,
            {'request_id': sample_ids}
        )


class VoteResource(TagasaurisNotifyResource):
    """ Entry point for externally gathered samples.
    """

    class Meta:
        resource_name = 'vote'
        list_allowed_methods = ['post']

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('add_from_tagasauris'),
                name='sample_add_from_tagasauris'),
        ]

    def add_from_tagasauris(self, request, **kwargs):
        """
            Initiates classification on passed url using classifier
            associated with job. Returns task id on success.
        """

        worker_id, results = self.parse_notification(request)

        try:
            worker = Worker.objects.get(external_id=worker_id)
        except Worker.DoesNotExist:
            return self.create_response(request,
                {'error': 'Worker not registered in database.'})

        quality_vote_ids = []
        for mediaobject_id, answers in results.iteritems():
            sample = SampleMapping.objects.get(
                external_id=mediaobject_id,
                crowscourcing_type=SampleMapping.TAGASAURIS
            ).sample

            for answer in answers:
                quality_vote = WorkerQualityVote(
                    worker=worker,
                    sample=sample
                )
                if answer['tag'] == 'broken':
                    quality_vote.label = LABEL_BROKEN
                elif answer['tag'] == 'yes':
                    quality_vote.label = LABEL_YES
                elif answer['tag'] == 'no':
                    quality_vote.label = LABEL_NO

        return self.create_response(
            request,
            {'quality_vote_ids': quality_vote_ids}
        )
