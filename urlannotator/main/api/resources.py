import json
import datetime
import pytz

from django.conf.urls import url
from django.conf import settings
from django.middleware.csrf import _sanitize_token, constant_time_compare
from django.core.urlresolvers import reverse
from itertools import chain

from tastypie.resources import ModelResource, Resource
from tastypie.authentication import Authentication
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpUnauthorized, HttpNotFound, HttpBadRequest
from django.utils.http import same_origin

from urlannotator.main.models import (Job, Sample, Worker, LABEL_BROKEN,
    LABEL_YES, LABEL_NO)
from urlannotator.classification.models import ClassifiedSample, TrainingSet
from urlannotator.crowdsourcing.models import (SampleMapping,
    WorkerQualityVote, BeatTheMachineSample)
from urlannotator.logging.models import LogEntry
from urlannotator.tools.utils import url_correct

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


def sanitize_label(label, err='Wrong label.'):
    label = label.lower()
    if label in ['yes', 'good', 'ok']:
        return LABEL_YES
    elif label in ['no', 'bad', 'wrong']:
        return LABEL_NO
    elif label in ['broken']:
        return LABEL_BROKEN
    else:
        raise ImmediateHttpResponse(
            HttpBadRequest(json.dumps({'error': err}))
        )


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
        alerts = LogEntry.objects.recent_for_job(num=0)

        limit = request.GET.get('limit', 10)
        offset = request.GET.get('offset', 0)

        page = reverse(
            'api_admin_updates',
            kwargs={
                'api_name': 'v1',
                'resource_name': 'admin',
            }
        )

        resp = paginate_list(alerts, limit, offset, page)
        resp['entries'] = map(self.alert_resource.raw_detail, resp['entries'])

        return self.create_response(request, resp)


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


class AlertResource(Resource):
    """
        Resource allowing API access to Jobs alerts.
    """
    def raw_detail(self, log):
        """
            Returns a raw JSON form of AlertResource.

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
        delta = datetime.datetime.now(pytz.utc) - log.date
        return {
            'id': log.id,
            'type': log.log_type,
            'job_id': log.job_id,
            'timedelta': round(delta.total_seconds()),
            'single_text': log.get_single_text(),
            'plural_text': log.get_plural_text(),
            'box': log.get_box(),
        }


class WorkerResource(Resource):
    """
        Resource allowing API access to Workers.
    """
    def raw_detail(self, worker_id, job_id):
        """
            Returns worker's details in regards to given job.

            Response format:
            `id` - Integer. Worker's id.
            `urls_collected` - Integer. Number of urls collected.
            `hours_spent` - String. Decimal number of hours spent in the job.
            `votes_added` - Integer. Number of votes worker has done.
            `earned` - Float. Amount of money worker has earned in job.
            `start_time` - String. Work start time in format %Y-%m-%d %H:%M:%S
                           as of datetime.strftime().
            `name` - String. Name of the worker.
        """
        worker = Worker.objects.get(id=worker_id)
        job = Job.objects.get(id=job_id)

        start_time = worker.get_job_start_time(job)
        return {
            'id': worker.id,
            'urls_collected': worker.get_urls_collected_count_for_job(job),
            'hours_spent': worker.get_hours_spent_for_job(job),
            'votes_added': worker.get_votes_added_count_for_job(job),
            'earned': worker.get_earned_for_job(job),
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'name': worker.get_name(),
        }


class JobResource(ModelResource):
    """
        Resource allowing API access to Jobs
    """
    class Meta:
        queryset = Job.objects.all()
        resource_name = 'job'
        list_allowed_methods = ['get', 'post']
        authentication = SessionAuthentication()
        include_absolute_url = True

    def __init__(self, *args, **kwargs):
        self.classifier_resource = ClassifierResource()
        self.alert_resource = AlertResource()
        self.worker_resource = WorkerResource()
        super(JobResource, self).__init__(*args, **kwargs)

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(account=request.user.get_profile())

    def override_urls(self):
        return [
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
                r'worker/(?P<worker_id>[^/]+)/$' % self._meta.resource_name,
                self.wrap_view('worker'),
                name='api_job_worker'),
            url(r'^(?P<resource_name>%s)/(?P<job_id>[^/]+)/btm/'
                % self._meta.resource_name,
                self.wrap_view('btm'), name='api_job_btm'),
        ]

    def worker(self, request, **kwargs):
        """
            Returns worker's details.
        """
        self.method_check(request, allowed=['get'])
        self._check_job(request, **kwargs)
        job_id = kwargs.get('job_id', 0)
        job_id = sanitize_positive_int(job_id)
        worker_id = kwargs.get('worker_id', 0)
        worker_id = sanitize_positive_int(worker_id)

        return self.create_response(
            request,
            self.worker_resource.raw_detail(
                job_id=job_id,
                worker_id=worker_id,
            )
        )

    def btm(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        self._check_job(request, **kwargs)
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

    def get_detail(self, request, **kwargs):
        """
            Returns details of given job.

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
        self.method_check(request, allowed=['get'])
        kwargs['job_id'] = kwargs['pk']
        self._check_job(request, **kwargs)
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

        top_workers = job.get_top_workers(cache=True)
        top_workers = [self.worker_resource.raw_detail(job_id=job.id,
            worker_id=x.id) for x in top_workers]

        newest_votes = job.get_newest_votes(cache=True)

        urls_collected = job.get_urls_collected(cache=True)
        no_of_workers = job.get_no_of_workers()
        progress = job.get_progress(cache=True)
        progress_urls = job.get_progress_urls(cache=True)
        progress_votes = job.get_progress_votes(cache=True)
        votes_gathered = job.get_votes_gathered(cache=True)
        hours_spent = job.get_hours_spent(cache=True)

        response = {
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'urls_to_collect': job.no_of_urls,
            'urls_collected': urls_collected,
            # 'classifier': reverse('api_classifier', kwargs={
            #     'api_name': 'v1',
            #     'resource_name': 'job',
            #     'job_id': job_id,
            # }),
            'feed': '/api/v1/job/%d/feed/?format=json' % job_id,
            'no_of_workers': no_of_workers,
            'cost': job.get_cost(cache=True),
            'budget': job.budget,
            'progress': progress,
            'hours_spent': hours_spent,
            'top_workers': top_workers,
            'newest_votes': newest_votes,
            'progress_urls': progress_urls,
            'progress_votes': progress_votes,
            'votes_gathered': votes_gathered,
        }

        if job.is_own_workforce():
            additional = {
                'sample_gathering_url': job.get_sample_gathering_url(),
                'sample_voting_url': job.get_voting_url(),
            }
            response = dict(chain(response.iteritems(), additional.iteritems()))

        return self.create_response(request, response)

    def updates_feed(self, request, **kwargs):
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
        self._check_job(request, **kwargs)

        limit = request.GET.get('limit', ALERTS_DEFAULT_LIMIT)
        offset = request.GET.get('offset', ALERTS_DEFAULTS_OFFSET)

        job_id = kwargs.get('job_id', 0)
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

        base_url = reverse(
            "api_job_updates_feed",
            kwargs={
                'api_name': 'v1',
                'resource_name': 'job',
                'job_id': job_id,
            }
        )

        resp = paginate_list(
            entry_list=alerts,
            limit=limit,
            offset=offset,
            page=base_url,
        )
        alerts = map(self.alert_resource.raw_detail, resp['entries'])
        resp['entries'] = alerts

        return self.create_response(request, resp)

    def _check_job(self, request, **kwargs):
        """
            Checks if user can access requested job.
        """
        self.is_authenticated(request)
        job_id = kwargs.get('job_id', None)
        job_id = sanitize_positive_int(job_id)

        try:
            job = Job.objects.get(id=kwargs['job_id'])
        except Job.DoesNotExist:
            raise ImmediateHttpResponse(
                HttpNotFound(json.dumps({'error': 'Wrong job.'}))
            )

        if request.user.is_authenticated():
            account = request.user.get_profile()
            if job.account != account and not request.user.is_superuser:
                raise ImmediateHttpResponse(
                    HttpNotFound(json.dumps({'error': 'Wrong job.'}))
                )
        else:
            raise ImmediateHttpResponse(
                HttpUnauthorized(json.dumps({'error': 'Wrong job.'}))
            )

        return None

    def classifier_history(self, request, **kwargs):
        """
            Returns classifier's classification history.
        """
        self.method_check(request, allowed=['get'])
        self._check_job(request, **kwargs)

        return self.classifier_resource.classify_history(request, **kwargs)

    def classifier_status(self, request, **kwargs):
        """
            Returns classification status.
        """
        self.method_check(request, allowed=['get'])
        self._check_job(request, **kwargs)
        return self.classifier_resource.classify_status(request, **kwargs)

    def classifier_classify(self, request, **kwargs):
        """
            Returns classifier details for given job.
        """
        self.method_check(request, allowed=['post'])
        self._check_job(request, **kwargs)

        return self.classifier_resource.classify(request, **kwargs)

    def classifier(self, request, **kwargs):
        """
            Returns classifier details for given job.
        """
        self.method_check(request, allowed=['get'])
        self._check_job(request, **kwargs)

        return self.classifier_resource.get_detail(request, **kwargs)


class SampleResource(ModelResource):
    """ Entry point for externally gathered samples.
    """

    class Meta:
        resource_name = 'sample'
        list_allowed_methods = ['post']

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
            if Sample.objects.filter(domain=domain, job=job
                    ).count() >= job.same_domain_allowed:
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
        worker_id = data.get('worker_id')

        classified_sample = BeatTheMachineSample.objects.create_by_worker(
            job=job,
            url=url,
            label='',
            expected_output=LABEL_YES,
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
            resp['points'] = classified_sample.points
            resp['btm_status'] = classified_sample.btm_status_mapping()

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
                        label = None
                        if answer['tag'] == 'broken':
                            label = LABEL_BROKEN
                        elif answer['tag'] == 'yes':
                            label = LABEL_YES
                        elif answer['tag'] == 'no':
                            label = LABEL_NO

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
