import json
import datetime
import pytz

from django.conf.urls import url
from django.conf import settings
from django.middleware.csrf import _sanitize_token, constant_time_compare
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from tenclouds.crud import fields, resources
from tenclouds.crud.paginator import Paginator
from tenclouds.crud import actions

from tastypie.resources import ModelResource, Resource
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpNotFound, HttpBadRequest
from django.utils.http import same_origin

from urlannotator.main.models import (Job, Sample, Worker, LABEL_BROKEN,
    LABEL_YES, LABEL_NO, make_label, WorkerJobAssociation)
from urlannotator.classification.models import ClassifiedSample
from urlannotator.crowdsourcing.models import (SampleMapping,
    WorkerQualityVote, BeatTheMachineSample)
from urlannotator.logging.models import LogEntry
from urlannotator.tools.utils import url_correct
from urlannotator.payments.models import BTMBonusPayment

import logging
log = logging.getLogger(__name__)


class SessionAuthentication(Authentication):
    def is_authenticated(self, request, **kwargs):
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return request.user.is_authenticated()

        if getattr(request, '_dont_enforce_csrf_checks', False):
            return request.user.is_authenticated()

        csrf_token = _sanitize_token(request.COOKIES.get(
            settings.CSRF_COOKIE_NAME, ''))

        if request.is_secure():
            referer = request.META.get('HTTP_REFERER')

            if referer is None:
                return False

            good_referer = 'https://%s/' % request.get_host()

            if not same_origin(referer, good_referer):
                return False

        request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

        if not constant_time_compare(request_csrf_token, csrf_token):
            return False

        return request.user.is_authenticated()

    def get_identifier(self, request):
        return request.user.username


def sanitize_positive_int(value, err='Wrong parameters.'):
    try:
        value = int(value)
    except:
        raise ImmediateHttpResponse(
            HttpBadRequest(json.dumps({'error': err}))
        )

    if value < 0:
        raise ImmediateHttpResponse(
            HttpBadRequest(json.dumps({'error': err}))
        )
    return value


def paginate_list(entry_list, limit, offset, page):
    """
        Handles pagination of list of items from arguments into a paginated
        list. Limit and offset values are sanitized on their own.

        Returns a dictionary:
        `next_page` - String. URL to get next page from.
        `entries` - List. List of entries.
        `total_count` - Integer. Total count of items in the passed list.
        `count` - Integer. Count of items in the result list.
        `offset` - Integer. First item's offset.
        `limit` - Integer. List's max length.
    """
    try:
            limit = sanitize_positive_int(limit)
            offset = sanitize_positive_int(offset)
    except:
        raise ImmediateHttpResponse(
            HttpBadRequest(json.dumps({'error': 'Wrong parameters.'}))
        )

    total_count = len(entry_list)

    response = {}
    response['total_count'] = total_count
    return_list = entry_list[offset:limit]
    response['count'] = len(return_list)

    new_offset = offset + limit
    if new_offset >= total_count:
        # We have reached the end of list. Return current URL.
        next_page = '%s?limit=%s&offset=%s' % (page, limit, offset)
    else:
        next_page = '%s?limit=%s&offset=%s' % (page, limit, new_offset)

    response['next_page'] = next_page
    response['entries'] = return_list
    response['limit'] = limit
    response['offset'] = offset
    return response


class AdminSessionAuthentication(SessionAuthentication):
    def is_authenticated(self, request, **kwargs):
        res = super(AdminSessionAuthentication, self).is_authenticated(
            request, **kwargs
        )
        if res:
            return request.user.is_superuser
        return res


class AdminResource(Resource):
    """
        Resource allowing API access to admin resources.
    """
    class Meta:
        resource_name = 'admin'
        authentication = AdminSessionAuthentication()

    def __init__(self, *args, **kwargs):
        self.alert_resource = AlertResource()

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/updates/$'
                % self._meta.resource_name,
                self.wrap_view('updates'), name='api_admin_updates'),
            url(r'^(?P<resource_name>%s)/job/(?P<job_id>[^/]+)/stop_sample_gathering/$'
                % self._meta.resource_name,
                self.wrap_view('stop_sample_gathering'), name='api_stop_sample_gathering'),
            url(r'^(?P<resource_name>%s)/job/(?P<job_id>[^/]+)/stop_voting/$'
                % self._meta.resource_name,
                self.wrap_view('stop_voting'), name='api_stop_voting'),
        ]

    def stop_sample_gathering(self, request, **kwargs):
        """
            Stops underlying job's sample gathering.

            Parameters (GET):
            None
        """
        self.is_authenticated(request)
        job_id = kwargs.get('job_id', 0)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(request,
                {'error': "Job doesn't exist."},
                response_class=HttpNotFound,
            )
        try:
            job.stop_sample_gathering()
            return self.create_response(request,
                {'result': 'SUCCESS'})
        except Exception, e:
            return self.create_response(request,
                {'error': e.message})

    def stop_voting(self, request, **kwargs):
        """
            Stops underlying job's sample gathering.
        """
        self.is_authenticated(request)
        job_id = kwargs.get('job_id', 0)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(request,
                {'error': "Job doesn't exist."},
                response_class=HttpNotFound,
            )
        try:
            job.stop_voting()
            return self.create_response(request,
                {'result': 'SUCCESS'})
        except Exception, e:
            return self.create_response(request,
                {'error': e.message})

    def updates(self, request, **kwargs):
        """
            Returns list of all updates in the system.

            Parameters (GET):
            'limit' - Integer. Maximum number of alerts to return.
                      Defaults to 10.
            'offset' - Integer. Offset to start listing alerts from.
                       Defaults to 0.
        """
        self.is_authenticated(request)
        res = AlertResource()
        return res.get_list(request, **kwargs)



class ClassifiedSampleResource(Resource):
    """
        Resource allowing API access to classified samples.
    """
    def raw_detail(self, class_id):
        """
            Returns raw JSON form of ClassifiedSampleResource.

            Format:
            `id` - Integer. Classified sample's id.
            `screenshot` - String. Classified Sample's screenshot URL.
            `url` - String. Classified sample's URL.
            `job_id` - Integer. Job's id.
            `label_probability` - Dict. Dictionary of each label's
                                  probabilities.
                `Yes` - Float. Probability of Yes label.
                `No` - Float. Probability of No label.
            `label` - String. Sample's label.
            `sample_url` - String. URL you can query connected sample from.
            'finished' - Boolean. Whether the sample's classification has
                         finished.
            `sample_url` - String. URL pointing to sample's data view.
        """
        class_sample = ClassifiedSample.objects.get(id=class_id)
        screenshot = ''
        if class_sample.sample:
            screenshot = class_sample.sample.get_small_thumbnail_url()

        label_probability = {
            LABEL_YES: class_sample.get_yes_probability(),
            LABEL_NO: class_sample.get_no_probability(),
            LABEL_BROKEN: class_sample.get_broken_probability(),
        }

        data = {
            'id': class_sample.id,
            'screenshot': screenshot,
            'url': class_sample.url,
            'job_id': class_sample.job_id,
            'label_probability': label_probability,
            'label': class_sample.label,
            'finished': class_sample.is_successful(),
        }

        if class_sample.sample:
            data['sample_url'] = reverse('project_data_detail', kwargs={
                'id': class_sample.job_id,
                'data_id': class_sample.sample.id,
            })

        return data


class ClassifierResource(Resource):
    """
        Resource allowing API access to Job's classifier.
    """
    class Meta:
        resource_name = 'classifier'
        list_allowed_methods = ['get', 'post']

    def __init__(self, *args, **kwargs):
        self.classified_sample_resource = ClassifiedSampleResource()
        super(ClassifierResource, self).__init__(*args, **kwargs)

    def get_detail(self, request, *args, **kwargs):
        job_id = kwargs.get('job_id', 0)
        job = Job.objects.get(id=job_id)

        yes_labels = []
        no_labels = []
        broken_labels = []

        for sample in job.sample_set.all().iterator():
            label = sample.get_classified_label()
            if label == LABEL_YES:
                yes_labels.append(sample)
            elif label == LABEL_NO:
                no_labels.append(sample)

        return self.create_response(
            request, {
                'absolute_url': reverse(
                    'api_classifier',
                    kwargs={
                        'resource_name': 'job',
                        'job_id': job_id,
                        'api_name': 'v1',
                    }
                ),
                'performance': job.get_classifier_performance(),
                'classify_url': reverse(
                    'api_classifier_classify',
                    kwargs={
                        'resource_name': 'job',
                        'job_id': job_id,
                        'api_name': 'v1',
                    }
                ),
                'yes_count': len(yes_labels),
                'no_count': len(no_labels),
                'broken_count': len(broken_labels),
            }
        )

    def classify(self, request, **kwargs):
        """
            Initiates classification on given url.
            Returns request id on success.

            Parameters (POST):
            `url` - String. URL to classify.
            'urls' - String. Optional. JSON list of urls to classify. If passed,
                     `url` is ignored. If used, `request_id` is a list of
                     classification requests.

            Response format:
            `error` - Only when error occured. String value of the error.
            `request_id` - Integer. Id of classification request.
            `status_url` - String. URL where you can query for request status.
        """
        self.method_check(request, allowed=['post'])

        job_id = kwargs.get('job_id', None)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong job.'},
                response_class=HttpNotFound,
            )

        classify_urls = request.POST.get('urls', None)
        if classify_urls:
            classify_urls = json.loads(classify_urls)
            request_ids = []
            for class_url in classify_urls:
                # Empty url case
                if not class_url:
                    continue

                classified_sample = ClassifiedSample.objects.create_by_owner(
                    job=job,
                    url=class_url,
                    label=''
                )
                request_ids.append({
                    'id': classified_sample.id,
                    'url': class_url,
                })
        else:
            classify_url = request.POST.get('url', None)
            if not classify_url:
                return self.create_response(
                    request,
                    {'error': 'Wrong url.'},
                    response_class=HttpNotFound,
                )
            classified_sample = ClassifiedSample.objects.create_by_owner(
                job=job,
                url=classify_url,
                label=''
            )
            request_ids = classified_sample.id

        return self.create_response(
            request,
            {
                'request_id': request_ids,
                'status_url': reverse(
                    'api_classifier_status',
                    kwargs={
                        'resource_name': 'job',
                        'api_name': 'v1',
                        'job_id': job_id,
                    }
                ),
            }
        )

    def classify_status(self, request, **kwargs):
        """
            Checks classification status of user-requested classification.
            If it's in progress, suitable result is returned.
            If it's finished, classification results are returned.

            Parameters (GET):
            `request_id` - Integer. Id of request to check status of.

            Response format:
            `error` - String. Value of error occured. Only included when error
                      occured.
            `status` - String. One of 'PENDING', 'SUCCESS'.
            `sample`- Dict. Only if status == 'SUCCESS'.
                      ClassifiedSample resource.
        """
        self.method_check(request, allowed=['get'])
        job_id = kwargs.get('job_id', None)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong job.'},
                response_class=HttpNotFound,
            )

        request_id = request.GET.get('request_id', 0)
        request_id = sanitize_positive_int(request_id)

        try:
            classified_sample = ClassifiedSample.objects.get(
                job=job,
                id=request_id,
            )
        except ClassifiedSample.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong request id.'},
                response_class=HttpNotFound,
            )

        resp = {}
        status = classified_sample.get_status()
        resp['status'] = status
        if classified_sample.is_successful():
            resp['sample'] = self.classified_sample_resource.raw_detail(
                class_id=classified_sample.id,
            )

        return self.create_response(request, resp)

    def classify_history(self, request, **kwargs):
        """
            Returns classifier's API classification history.

            Response format:
            `count` - Integer. Count of all entries.
            `offset` - Integer. Number of the first entry in the list.
                       Defaults to 0.
            `limit` - Integer. Number of entries to include.
            `next_page` - String. URL to query next entries list from.
            `entries` - List. List of ClassifiedSample resources sorted from
                        newest to oldest.
        """
        self.method_check(request, allowed=['get'])

        job_id = kwargs.get('job_id', 0)
        job_id = sanitize_positive_int(job_id)

        offset = request.GET.get('offset', 0)
        limit = request.GET.get('limit', 0)
        base_url = reverse(
            'api_classifier_history',
            kwargs={
                'api_name': 'v1',
                'resource_name': 'job',
                'job_id': job_id,
            }
        )

        samples = ClassifiedSample.objects.filter(job_id=job_id).order_by('-id')
        resp = paginate_list(
            entry_list=samples,
            limit=limit,
            offset=offset,
            page=base_url,
        )
        entries = [e.id for e in resp['entries']]
        resp['entries'] = map(self.classified_sample_resource.raw_detail,
            entries)
        return self.create_response(request, resp)

ALERTS_DEFAULT_LIMIT = 20
ALERTS_DEFAULTS_OFFSET = 0


class AlertResource(resources.ModelResource):
    """
        Resource allowing API access to Jobs alerts.

        `id` - Integer. Alert's id.
        `type` - Integer. Alert's type.
        `job_id` - Integer. Alert's job's id.
        `timedelta` - Integer. Difference between current time and time of
                      creation.
        `single_text` - String. Text of the alert in singular form.
        `plural_text` - String. Text of the alert in plural form.
        `box` - Dictionary. Contains data about alert's update box
                template.
            `Title` - String. Box's title.
            `Text` - String. Box's text.
            `Image_url` - String. Box's image that's displayed on the left
                          hand side.
            `By` - String. Optional. Name of the worker that has caused
                   this event. Can be an empty string, and should be
                   considered as empty in that case.
            `By_id` - Integer. Optional. Id of the worker that has caused
                      this event. Can be 0, or empty, and should be
                      considered as empty in that case.
            `Job_id` - Integer. Alert's job's id.
    """
    id = fields.IntegerField(attribute='id')
    type = fields.IntegerField(attribute='log_type')
    job = fields.ForeignKey('urlannotator.main.api.resources.JobResource', 'job')
    job_id = fields.IntegerField(attribute='job_id')
    timedelta = fields.IntegerField()
    single_text = fields.CharField()
    plural_text = fields.CharField()
    box = fields.DictField()

    class Meta:
        authentication = SessionAuthentication()
        per_page = [4, 10, 20, 100, 200]
        paginator = Paginator
        ordering = ['date']
        fields = ['id', 'job_id']

    def apply_authorization_limits(self, request, object_list):
        object_list = super(JobFeedResource, self).apply_authorization_limits(
            request, object_list)
        if not request.user.is_superuser:
            return object_list.filter(job__account=request.user.get_profile())
        return object_list

    def dehydrate_box(self, bundle):
        return bundle.obj.get_box()

    def dehydrate_plural_text(self, bundle):
        return bundle.obj.get_plural_text()

    def dehydrate_single_text(self, bundle):
        return bundle.obj.get_single_text()

    def dehydrate_timedelta(self, bundle):
        delta = datetime.datetime.now(pytz.utc) - bundle.obj.date
        return round(delta.total_seconds())

    def obj_get_list(self, request, job_id=0, **kwargs):
        if job_id == 0 and request.user.is_superuser:
            alerts = LogEntry.objects.recent_for_job(
                num=0,
            )
            return alerts

        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong parameters.'},
                response_class=HttpBadRequest,
            )

        alerts = LogEntry.objects.recent_for_job(
            job=job,
            num=0,
        )
        return alerts


class WorkerResource(resources.ModelResource):
    """
        Resource allowing API access to Workers.
    """
    id = fields.CharField(attribute='external_id')
    name = fields.CharField()

    class Meta:
        resource_name = 'worker'
        list_allowed_methods = ['get', ]
        per_page = 10
        queryset = Worker.objects.all()
        ordering = ['id']
        fields = ['id']

    def dehydrate_name(self, bundle):
        return bundle.obj.get_name()


class JobFeedResource(Resource):

    class Meta:
        authentication = SessionAuthentication()
        per_page = 10
        paginator = Paginator
        list_allowed_methods = ['get', ]

    def apply_authorization_limits(self, request, object_list):
        object_list = super(JobFeedResource, self).apply_authorization_limits(
            request, object_list)
        if not request.user.is_superuser:
            return object_list.filter(job__account=request.user.get_profile())
        return object_list

    def obj_get(self, request, pk, *args, **kwargs):
        return {}

    def obj_get_list(self, request, job_id, *args, **kwargs):
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong parameters.'},
                response_class=HttpBadRequest,
            )

        alerts = LogEntry.objects.recent_for_job(
            job=job,
            num=0,
        )
        return alerts


class OwnerAuthorization(Authorization):
    def __init__(self, attribute, *args, **kwargs):
        self.attributes = attribute.split('.')
        super(Authorization, self).__init__(*args, **kwargs)

    def is_authorized(self, request, object=None):
        if request.user.is_superuser or object is None:
            return True

        obj = object
        for attr in self.attributes:
            obj = getattr(obj, attr)

        return obj == request.user


class OwnerModelResource(resources.ModelResource):
    def cached_obj_get(self, request, **kwargs):
        bundle = super(OwnerModelResource, self).cached_obj_get(
            request=request, **kwargs)

        if self._meta.authorization.is_authorized(
            request=request, object=bundle):
            return bundle

        raise ObjectDoesNotExist()


class JobResource(OwnerModelResource):
    """
        Resource allowing API access to Jobs

        Response format:
        `id` - Integer. Job's id.
        `title` - String. Job's title.
        `description` - String. Job's description.
        `urls_to_collect` - Integer. URLs to collected defined at creation.
        `urls_collected` - Integer. URLs already collected.
        `classifier` - String. URL classifier can be queried from.
        `feed` - String. URL updates feed can be queried from.
        `no_of_workers` - Integer. Number of workers in the job.
        `cost` - String. Actual decimal cost of the job.
        `budget` - String. Decimal job's budget.
        `progress` - Integer. Percentage of job's completion.
        `hours_spent` - Integer. No. of hours workers have spent on the job.
        `sample_gathering_url` - String. URL people can gather samples to.
                                 (Only Own Workforce jobs)
        `sample_voting_url` - String. URL people can vote on sample labels.
                              (Only Own Workforce jobs)
    """
    urls_to_collect = fields.IntegerField(attribute='no_of_urls')
    urls_collected = fields.IntegerField(attribute='collected_urls')
    no_of_workers = fields.IntegerField()
    cost = fields.DecimalField()
    progress = fields.IntegerField()
    hours_spent = fields.IntegerField()
    sample_gathering_url = fields.CharField()
    sample_voting_url = fields.CharField()
    votes_gathered = fields.IntegerField()
    progress_urls = fields.IntegerField()
    progress_votes = fields.IntegerField()
    newest_votes = fields.ListField()
    top_workers = fields.ListField()
    feed = fields.CharField()
    workers = fields.ToManyField(
        'urlannotator.main.api.resources.WorkerJobAssociationResource',
        'workerjobassociation_set'
    )
    samples = fields.ToManyField(
        'urlannotator.main.api.resources.SampleResource',
        'sample_set'
    )

    class Meta:
        queryset = Job.objects.all()
        resource_name = 'job'
        list_allowed_methods = ['get', 'post']
        authentication = SessionAuthentication()
        authorization = OwnerAuthorization(attribute='account.user')
        include_absolute_url = True
        fields = ['id', 'title', 'description', 'budget']

    def __init__(self, *args, **kwargs):
        self.classifier_resource = ClassifierResource()
        self.alert_resource = AlertResource()
        self.worker_resource = WorkerResource()
        super(JobResource, self).__init__(*args, **kwargs)

    def apply_authorization_limits(self, request, object_list):
        object_list = super(JobResource, self).apply_authorization_limits(
            request, object_list)
        if not request.user.is_superuser:
            return object_list.filter(account=request.user.get_profile())
        return object_list

    def dehydrate_feed(self, bundle):
        return self._build_reverse_url('api_job_updates_feed', kwargs={
            'api_name': 'v1',
            'resource_name': 'job',
            'job_id': bundle.obj.id,
        })

    def dehydrate_top_workers(self, bundle):
        wr = WorkerJobAssociationResource()
        worker_list = []
        for assoc in bundle.obj.get_top_workers(cache=True):
            bundle = wr.build_bundle(obj=assoc)
            worker_list.append(wr.full_dehydrate(bundle))
        return worker_list

    def dehydrate_newest_votes(self, bundle):
        return bundle.obj.get_newest_votes(cache=True)

    def dehydrate_progress_votes(self, bundle):
        return bundle.obj.get_progress_votes(cache=True)

    def dehydrate_progress_urls(self, bundle):
        return bundle.obj.get_progress_urls(cache=True)

    def dehydrate_votes_gathered(self, bundle):
        return bundle.obj.get_votes_gathered(cache=True)

    def dehydrate_sample_gathering_url(self, bundle):
        return bundle.obj.get_sample_gathering_url()

    def dehydrate_sample_voting_url(self, bundle):
        return bundle.obj.get_voting_url()

    def dehydrate_hours_spent(self, bundle):
        return bundle.obj.get_hours_spent(cache=True)

    def dehydrate_progress(self, bundle):
        return bundle.obj.get_progress(cache=True)

    def dehydrate_cost(self, bundle):
        return bundle.obj.get_cost(cache=True)

    def dehydrate_no_of_workers(self, bundle):
        return bundle.obj.get_no_of_workers()

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/estimate/'
                % self._meta.resource_name,
                self.wrap_view('estimate_cost'), name='estimate_cost'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classifier/$'
                % self._meta.resource_name,
                self.wrap_view('classifier'), name='api_classifier'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classifier/classify/$'
                % self._meta.resource_name,
                self.wrap_view('classifier_classify'),
                name='api_classifier_classify'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classifier/status/$'
                % self._meta.resource_name,
                self.wrap_view('classifier_status'),
                name='api_classifier_status'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/classifier/history/$'
                % self._meta.resource_name,
                self.wrap_view('classifier_history'),
                name='api_classifier_history'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/feed/$'
                % self._meta.resource_name,
                self.wrap_view('updates_feed'),
                name='api_job_updates_feed'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/'
                r'worker/(?P<worker>.*)$' % self._meta.resource_name,
                self.wrap_view('worker'),
                name='api_job_worker'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/'
                r'sample/(?P<sample>.*)$' % self._meta.resource_name,
                self.wrap_view('sample'),
                name='api_job_sample'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/btm/'
                % self._meta.resource_name,
                self.wrap_view('btm'), name='api_job_btm'),
        ]

    def worker(self, request, **kwargs):
        """
            Returns worker's details, list or actions, depending on the ID.
        """
        self.method_check(request, allowed=['get', 'post'])
        job_id = kwargs.pop('job_id', 0)
        job_id = sanitize_positive_int(job_id)
        worker_id = kwargs.pop('worker', '')
        wr = WorkerJobAssociationResource()
        if worker_id == 'schema/':
            return wr.get_schema(request)
        elif worker_id == '':
            return wr.get_list(request, job_id=job_id)
        elif worker_id == '_actions/':
            return wr.dispatch_actions(request, job_id=job_id,
                worker_id=worker_id, **kwargs)

        worker_id = sanitize_positive_int(worker_id)

        return self.create_response(
            request,
            self.worker_resource.get_detail(request,
                job_id=job_id,
                worker_id=worker_id,
            )
        )

    def sample(self, request, **kwargs):
        """
            Returns worker's details.
        """
        self.method_check(request, allowed=['get', 'post'])
        job_id = kwargs.pop('job_id', 0)
        job_id = sanitize_positive_int(job_id)
        sample_id = kwargs.pop('sample', '')
        sr = SampleResource()
        if sample_id == 'schema/':
            return sr.get_schema(request)
        elif sample_id == '':
            return sr.get_list(request, job_id=job_id)
        elif sample_id == '_actions/':
            return sr.dispatch_actions(request, job_id=job_id,
                sample_id=sample_id, **kwargs)

        sample_id = sanitize_positive_int(sample_id)

        return self.create_response(
            request,
            sr.get_detail(request,
                job_id=job_id,
                sample_id=sample_id,
            )
        )

    def btm(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        job_id = kwargs.get('job_id', 0)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong parameters.'},
                response_class=HttpNotFound,
            )

        samples = request.POST.get('samples', '[]')
        samples = json.loads(samples)

        for sample in samples:
            sample_id = sanitize_positive_int(sample)
            # TODO: sample_id -> sample
            job.add_btm_verified_sample(sample_id)

        return self.create_response(
            request,
            {'status': 'ok'},
        )

    def updates_feed(self, request, job_id, **kwargs):
        """
            Returns updates feed for given job.

            Parameters (GET):
            `limit` - Optional. Number of alerts to include per page.
                      Defaults to 20.
            `offset` - Optional. Offset from which to start alert's list.
                       Defaults to 0.

            Response format:
            `total_count` - Integer. Total number of alerts.
            `count` - Integer. Number of alerts included.
            `next_page` - String. URL to get next page of alerts from.
            `alerts` - List. List of AlertResource, sorted from newest to
                       oldest.
        """
        self.method_check(request, allowed=['get'])
        res = AlertResource()
        return res.get_list(request, job_id=job_id, **kwargs)

    def classifier_history(self, request, **kwargs):
        """
            Returns classifier's classification history.
        """
        self.method_check(request, allowed=['get'])

        return self.classifier_resource.classify_history(request, **kwargs)

    def classifier_status(self, request, **kwargs):
        """
            Returns classification status.
        """
        self.method_check(request, allowed=['get'])
        return self.classifier_resource.classify_status(request, **kwargs)

    def classifier_classify(self, request, **kwargs):
        """
            Returns classifier details for given job.
        """
        self.method_check(request, allowed=['post'])

        return self.classifier_resource.classify(request, **kwargs)

    def classifier(self, request, **kwargs):
        """
            Returns classifier details for given job.
        """
        self.method_check(request, allowed=['get'])

        return self.classifier_resource.get_detail(request, **kwargs)

    def estimate_cost(self, request, **kwargs):
        self.method_check(request, allowed=['get'])

        data_source = int(request.GET.get('data_source'))
        no_of_urls = request.GET.get('no_of_urls', 0)
        no_of_urls = int(no_of_urls if no_of_urls else 0)

        cost = Job.estimate_cost(data_source, no_of_urls)

        return self.create_response(
            request,
            {'cost': cost},
        )


class WorkerJobAssociationResource(resources.ModelResource):
    """
        Resource allowing API access to worker's data inside a job.
    """
    start_time = fields.DateTimeField(attribute='started_on')
    hours_spent = fields.DecimalField(attribute='worked_hours')
    worker = fields.ForeignKey(WorkerResource, 'worker', full=True)
    urls_collected = fields.IntegerField(title='Urls collected')
    votes_added = fields.IntegerField(title='Votes added')
    name = fields.CharField(title='Name', url='worker_job_url')
    bonus_gathered = fields.IntegerField(title='Bonus points gathered')
    bonus_paid = fields.IntegerField(title='Bonus points paid')
    bonus_pending = fields.IntegerField(title='Bonus points pending')
    id = fields.IntegerField(attribute='id', title=' ')

    class Meta:
        resource_name = 'worker_association'
        list_allowed_methods = ['get', ]
        per_page = [10, 20, 50, 100, 200]
        queryset = WorkerJobAssociation.objects.all()
        fields = ['id', 'name', 'urls_collected', 'votes_added',
                  'bonus_gathered', 'bonus_paid', 'bonus_pending']

    def apply_authorization_limits(self, request, obj_list):
        obj_list = super(WorkerJobAssociationResource, self).\
            apply_authorization_limits(request, obj_list)
        return obj_list.filter(job__account__user=request.user)

    def dehydrate_worker_job_url(self, bundle):
        return reverse('project_worker_view', kwargs={
            'id': bundle.obj.job_id,
            'worker_id': bundle.obj.worker_id,
        })

    def dehydrate_bonus_pending(self, bundle):
        return bundle.obj.btm_pending

    def dehydrate_bonus_paid(self, bundle):
        return bundle.obj.btm_paid

    def dehydrate_bonus_gathered(self, bundle):
        return bundle.obj.btm_gathered

    def dehydrate_name(self, bundle):
        return bundle.obj.worker.get_name()

    def dehydrate_urls_collected(self, bundle):
        return bundle.obj.get_urls_collected()

    def dehydrate_votes_added(self, bundle):
        return bundle.obj.get_votes_added()

    def obj_get_list(self, request, job_id=None, **kwargs):
        objs = super(WorkerJobAssociationResource, self).obj_get_list(
                request=request, **kwargs)
        if job_id is None:
            return objs

        job_id = sanitize_positive_int(job_id)
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(request,
                {'error': 'Wrong job.'},
                response_class=HttpNotFound)

        return objs.filter(job=job)

    @actions.action_handler(name='Pay out BTM bonus')
    def pay_btm_bonus(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        job_id = kwargs.get('job_id', 0)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
            if request.user != job.account.user and not request.user.is_superuser:
                return self.create_response(
                    request,
                    {'error': 'Wrong parameters.'},
                    response_class=HttpBadRequest,
                )
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong parameters.'},
                response_class=HttpNotFound,
            )

        workers = request.POST.get('bonus', '[]')
        workers = json.loads(workers)

        for worker in workers:
            worker_id = sanitize_positive_int(worker)
            worker = Worker.objects.get(id=worker_id)
            BTMBonusPayment.objects.create_for_worker(worker, job)

        return self.create_response(
            request,
            {'status': 'ok'},
        )


class SampleResource(resources.ModelResource):
    """ Entry point for externally gathered samples.
    """
    id = fields.IntegerField(attribute='id')
    job = fields.ForeignKey(JobResource, 'job')
    url = fields.CharField(title='URL', attribute='url', url='sample_url')
    screenshot = fields.CharField(title='Preview', attribute='screenshot')
    small_thumb = fields.CharField()
    large_thumb = fields.CharField()
    votes = fields.DictField(title='Voting')
    gold_sample = fields.CharField(title='Gold Sample')
    added_on = fields.DateTimeField(title='Added on', attribute='added_on')

    class Meta:
        resource_name = 'sample'
        queryset = Sample.objects.all()
        list_allowed_methods = ['get', 'post']
        per_page = [10, 20, 50, 100, 200, 500]
        authorization = OwnerAuthorization(attribute="job.account.user")
        fields = ['screenshot', 'url', 'added_on', 'votes', 'gold_sample']

    def apply_authorization_limits(self, request, obj_list):
        if not request.user.is_superuser:
            obj_list = obj_list.filter(job__account__user=request.user)
        return obj_list

    def dehydrate_sample_url(self, bundle):
        return reverse('project_data_detail', kwargs={
            'id': bundle.obj.job_id,
            'data_id': bundle.obj.id,
        })

    def dehydrate_large_thumb(self, bundle):
        return bundle.obj.get_large_thumbnail_url()

    def dehydrate_small_thumb(self, bundle):
        return bundle.obj.get_small_thumbnail_url()

    def dehydrate_added_on(self, bundle):
        return bundle.obj.added_on.strftime('%Y-%m-%d %H:%M')

    def dehydrate_gold_sample(self, bundle):
        label = bundle.obj.get_label()
        return label if label else '---'

    def dehydrate_votes(self, bundle):
        return {
            'yes': bundle.obj.get_yes_votes(cache=True),
            'no': bundle.obj.get_no_votes(cache=True),
            'broken': bundle.obj.get_broken_votes(cache=True),
        }

    def obj_get_list(self, request, job_id=None, **kwargs):
        if request.user.is_superuser and job_id is None:
            return Sample.objects.all()

        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
            if request.user != job.account.user and not request.user.is_superuser:
                return self.create_response(
                    request,
                    {'error': 'Wrong parameters.'},
                    response_class=HttpBadRequest,
                )
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong parameters.'},
                response_class=HttpNotFound,
            )

        return job.sample_set.all()

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/add/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('add_from_tagasauris'),
                name='add_from_tagasauris'),
        ]

    def add_from_tagasauris(self, request, **kwargs):
        try:
            job = Job.objects.get(id=kwargs['job_id'])
        except Job.DoesNotExist:
            return self.create_response(request,
                {'error': 'Wrong job.'},
                response_class=HttpNotFound)

        try:
            data = json.loads(request.raw_post_data)
        except ValueError:
            return self.create_response(request,
                {'error': 'Malformed request json.'},
                response_class=HttpBadRequest)

        url = data.get('url', None)
        worker_id = data.get('worker_id', None)
        if url is None or worker_id is None:
            return self.create_response(request,
                {'error': 'Wrong parameters.'},
                response_class=HttpBadRequest)

        collected = job.get_urls_collected()
        all_urls = job.no_of_urls <= collected
        if all_urls:
            return self.create_response(request, {
                'all': all_urls,
                'result': ''
            })

        sanitized_url = Sample.sanitize_url(url)
        if not url_correct(sanitized_url):
            result = 'malformed url'

        elif Sample.objects.filter(url=sanitized_url,
                job=job).count() == 0:
            domain = Sample.objects._domain(sanitized_url)
            if Sample.objects.filter(domain=domain,
                    job=job).count() >= job.same_domain_allowed:
                result = 'domain duplicate'
            else:
                res = Sample.objects.create_by_worker(
                    job_id=job.id,
                    url=url,
                    source_val=worker_id
                )
                res.get()
                collected += 1
                result = 'added'

        else:
            result = 'duplicate'

        all_urls = job.no_of_urls <= collected
        return self.create_response(request, {
            'result': result,
            'all': all_urls
        })


class BeatTheMachineResource(ModelResource):
    """ Entry point for beat the machine.
    """

    class Meta:
        resource_name = 'btm'
        list_allowed_methods = ['post', 'get']

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/add/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('btm_tagasauris'),
                name='btm_tagasauris'),
            url(r'^(?P<resource_name>%s)/status/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('btm_status'),
                name='btm_status'),
            url(r'^(?P<resource_name>%s)/data/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('btm_data'),
                name='btm_data'),
        ]

    def btm_tagasauris(self, request, **kwargs):
        self.method_check(request, allowed=['post'])

        try:
            job = Job.objects.get(id=kwargs['job_id'])
        except Job.DoesNotExist:
            return self.create_response(request,
                {'error': 'Wrong job.'},
                response_class=HttpNotFound)

        try:
            data = json.loads(request.raw_post_data)
        except ValueError:
            return self.create_response(request,
                {'error': 'Malformed request json.'},
                response_class=HttpBadRequest)

        required = ['url', 'worker_id']
        for req in required:
            if req not in data:
                return self.create_response(request,
                    {'error': 'Missing "%s" parameter.' % req},
                    response_class=HttpBadRequest)

        url = data.get('url')
        sanitized_url = Sample.sanitize_url(url)
        if not url_correct(sanitized_url):
            return self.create_response(request, {
                'result': 'malformed url',
            })

        if BeatTheMachineSample.objects.filter(job=job,
                url=sanitized_url).count() != 0:
            return self.create_response(request, {
                'result': 'duplicated url',
            })

        worker_id = data.get('worker_id')

        classified_sample = BeatTheMachineSample.objects.create_by_worker(
            job=job,
            url=url,
            label='',
            expected_output=LABEL_NO,
            worker_id=worker_id
        )

        return self.create_response(
            request,
            {
                'request_id': classified_sample.id,
                'status_url': reverse(
                    'btm_status',
                    kwargs={
                        'resource_name': 'btm',
                        'api_name': 'v1',
                        'job_id': job.id,
                    }
                ),
            }
        )

    def btm_status(self, request, **kwargs):
        """
            Checks classification status of BeatTheMachineSample.
            If it's in progress, suitable result is returned.
            If it's finished, labels match information is returned.

            Parameters (GET):
            `request_id` - Integer. Id of request to check status of.

            Response format:
            `error` - String. Value of error occured. Only included when error
                      occured.
            `status` - String. One of 'PENDING', 'SUCCESS'.
            `labels_matched`- Boolean. True if expected label equals classified
                              label. False otherwise.
        """
        self.method_check(request, allowed=['get'])
        job_id = kwargs.get('job_id', None)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong job.'},
                response_class=HttpNotFound,
            )

        request_id = request.GET.get('request_id', 0)
        request_id = sanitize_positive_int(request_id)

        try:
            classified_sample = BeatTheMachineSample.objects.get(
                job=job,
                id=request_id,
            )
        except BeatTheMachineSample.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong request id.'},
                response_class=HttpNotFound,
            )

        resp = {}
        status = classified_sample.get_status()
        resp['status'] = status
        if classified_sample.is_successful():
            min_p, max_p = classified_sample.get_min_max_points()
            resp['min_points'] = min_p
            resp['max_points'] = max_p
            resp['points'] = classified_sample.points
            resp['btm_status'] = classified_sample.btm_status_mapping()
            resp['label_probability'] = classified_sample.fixed_probability

        return self.create_response(request, resp)

    def btm_data(self, request, **kwargs):
        """
            Provides btm configuration for given job.

            Parameters (GET):

            Response format:
            `points_to_cash` - Integer. Informs worker of current points to
                cash conversion rate.
        """
        self.method_check(request, allowed=['get'])
        job_id = kwargs.get('job_id', None)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return self.create_response(
                request,
                {'error': 'Wrong job.'},
                response_class=HttpNotFound,
            )

        resp = {
            'points_to_cash': job.btm_points_to_cash
        }

        worker_id = request.GET.get('worker_id', None)
        if worker_id is not None:
            worker, created = Worker.objects.get_or_create_tagasauris(worker_id)
            resp.update({
                'gathered_points': worker.get_btm_bonus(job),
                'pending_verification': worker.get_btm_unverified(job).count(),
            })

        return self.create_response(request, resp)


class VoteResource(ModelResource):
    """ Entry point for externally gathered samples.
    """

    notification_required = ['results']

    class Meta:
        resource_name = 'vote'
        list_allowed_methods = ['post']

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/add/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('add_from_tagasauris'),
                name='sample_add_from_tagasauris'),
            url(r'^(?P<resource_name>%s)/btm/tagasauris/'
                '(?P<job_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('btm_from_tagasauris'),
                name='sample_btm_from_tagasauris'),
        ]

    def _add_from_tagasauris(self, request, vote_constructor, **kwargs):
        """
            Initiates classification on passed url using classifier
            associated with job. Returns task id on success.
        """

        data = json.loads(request.raw_post_data)

        self.method_check(request, allowed=['post'])
        for req in self.notification_required:
            if req not in data:
                return self.create_response(request,
                    {'error': 'Missing "%s" parameter.' % req},
                    response_class=HttpBadRequest)

        results = data['results']

        for worker_id, mediaobjects in results.iteritems():
            worker, created = Worker.objects.get_or_create_tagasauris(worker_id)

            for mediaobject_id, answers in mediaobjects.iteritems():
                try:
                    sample = SampleMapping.objects.get(
                        external_id=mediaobject_id,
                        crowscourcing_type=SampleMapping.TAGASAURIS
                    ).sample
                except Exception, e:
                    log.exception(
                        "AddVote: Exception caught when adding votes: "
                        "input %s, err %s" % (request.raw_post_data, e)
                    )
                    continue

                for answer in answers:
                    if answer['tag'] in ['yes', 'no', 'broken']:
                        label = make_label(answer['tag'])

                        if label is not None:
                            vote_constructor(
                                worker=worker,
                                sample=sample,
                                label=label
                            )
        return self.create_response(request, {})

    def add_from_tagasauris(self, request, **kwargs):
        """
            Initiates classification on passed url using classifier
            associated with job. Returns task id on success.
        """

        return self._add_from_tagasauris(request,
            vote_constructor=WorkerQualityVote.objects.new_vote,
            **kwargs)

    def btm_from_tagasauris(self, request, **kwargs):
        """
            Initiates classification on passed url using classifier
            associated with job. Returns task id on success.
        """

        return self._add_from_tagasauris(request,
            vote_constructor=WorkerQualityVote.objects.new_btm_vote,
            **kwargs)
