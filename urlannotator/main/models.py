import datetime
import requests
import hashlib
import urlparse
import odesk

from django.db import models
from django.db.models import F, Sum
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.timezone import now
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.cache import get_cache
from itertools import ifilter
from tenclouds.django.jsonfield.fields import JSONField

from urlannotator.flow_control import send_event
from urlannotator.tools.synchronization import POSIXLock
from urlannotator.settings import imagescale2
from urlannotator.crowdsourcing.tagasauris_helper import stop_job

import logging
log = logging.getLogger(__name__)

LABEL_BROKEN = 'Broken'
LABEL_YES = 'Yes'
LABEL_NO = 'No'
LABEL_CHOICES = (
    (LABEL_NO, 'No'),
    (LABEL_YES, 'Yes'),
    (LABEL_BROKEN, 'Broken')
)


class Account(models.Model):
    """
        Model representing additional user data. Used as user profile.
    """
    user = models.OneToOneField(User)
    activation_key = models.CharField(default='', max_length=100)
    email_registered = models.BooleanField(default=False)
    odesk_key = models.CharField(default='', max_length=100)
    odesk_uid = models.CharField(default='', max_length=100)
    full_name = models.CharField(default='', max_length=100)
    alerts = models.BooleanField(default=False)
    worker_entry = models.OneToOneField('Worker', null=True, blank=True)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)

# Job source types
JOB_SOURCE_ODESK_FREE = 0
JOB_SOURCE_OWN_WORKFORCE = 1
JOB_SOURCE_ODESK_PAID = 2

JOB_BASIC_DATA_SOURCE_CHOICES = (
    (JOB_SOURCE_OWN_WORKFORCE, 'Own workforce'),
)
JOB_ODESK_DATA_SOURCE_CHOICES = (
    (JOB_SOURCE_ODESK_FREE, 'Odesk free'),
    (JOB_SOURCE_ODESK_PAID, 'Odesk paid')
)

JOB_DATA_SOURCE_CHOICES = JOB_BASIC_DATA_SOURCE_CHOICES + \
    JOB_ODESK_DATA_SOURCE_CHOICES
JOB_TYPE_CHOICES = ((0, 'Fixed no. of URLs to collect'), (1, 'Fixed price'))

# Job status breakdown:
# Draft - template of a job, not active yet, can be started.
# Active - up and running job.
# Completed - job has reached it's goal. Possible BTM still running.
# Stopped - job has been stopped by it's owner.
# Initializing - job has been just created by user, awaiting initialization of
#                elements. An active job must've gone through this step.
#                Drafts DO NOT get this status.
JOB_STATUS_DRAFT = 0
JOB_STATUS_ACTIVE = 1
JOB_STATUS_COMPLETED = 2
JOB_STATUS_STOPPED = 3
JOB_STATUS_INIT = 4

JOB_STATUS_CHOICES = (
    (JOB_STATUS_DRAFT, 'Draft'),
    (JOB_STATUS_ACTIVE, 'Active'),
    (JOB_STATUS_COMPLETED, 'Completed'),
    (JOB_STATUS_STOPPED, 'Stopped'),
    (JOB_STATUS_INIT, 'Initializing')
)

# Job initialization progress flags. Set flags means the step is done.
JOB_FLAGS_TRAINING_SET_CREATED = 1  # Training set creation
JOB_FLAGS_GOLD_SAMPLES_DONE = 2  # Gold samples have been extracted
JOB_FLAGS_CLASSIFIER_CREATED = 4  # Classifier has been created
JOB_FLAGS_CLASSIFIER_TRAINED = 8  # Classifier has been trained

JOB_FLAGS_ALL = 1 + 2 + 4 + 8


class JobManager(models.Manager):
    def create_active(self, **kwargs):
        kwargs['status'] = 4
        kwargs['remaining_urls'] = kwargs.get('no_of_urls', 0)
        job = self.create(**kwargs)
        send_event('EventNewJobInitialization',
            job_id=job.id)
        return job

    def create_draft(self, **kwargs):
        kwargs['status'] = 0
        kwargs['remaining_urls'] = kwargs.get('no_of_urls', 0)
        return self.create(**kwargs)

    def get_active(self, **kwargs):
        els = super(JobManager, self).get_query_set().filter(status=1)
        return els


class Job(models.Model):
    """
        Model representing actual project that is start by user, and consists
        of gathering, verifying and classifying samples.
    """
    account = models.ForeignKey(Account)
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.IntegerField(default=0, choices=JOB_STATUS_CHOICES)
    progress = models.IntegerField(default=0)
    no_of_urls = models.PositiveIntegerField(default=0)
    data_source = models.IntegerField(default=1,
        choices=JOB_DATA_SOURCE_CHOICES)
    project_type = models.IntegerField(default=0, choices=JOB_TYPE_CHOICES)
    same_domain_allowed = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(default=0, decimal_places=2,
        max_digits=10)
    gold_samples = JSONField(default='[]')
    classify_urls = JSONField(default='[]')
    budget = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    remaining_urls = models.PositiveIntegerField(default=0)
    collected_urls = models.PositiveIntegerField(default=0)
    initialization_status = models.IntegerField(default=0)
    activated = models.DateTimeField(auto_now_add=True)
    votes_storage = models.CharField(max_length=25)
    quality_algorithm = models.CharField(max_length=25)
    btm_active = models.BooleanField(default=False)
    btm_to_gather = models.PositiveIntegerField(default=0)

    objects = JobManager()

    @models.permalink
    def get_absolute_url(self):
        return ('project_view', (), {
            'id': self.id,
        })

    def update_cache(self):
        """
            Forces cache recalculation.
        """
        self.get_hours_spent()
        self.get_progress()
        self.get_top_workers()

    def recreate_training_set(self, force=False):
        """
            Recreates a training set from quality algorithm and trains
            classifier on it.
        """
        from urlannotator.crowdsourcing.factories import quality_factory
        from urlannotator.classification.models import (TrainingSet,
            TrainingSample)

        if not self.has_new_votes() and not force:
            return

        quality_algorithm = quality_factory.create_algorithm(self)
        decisions = quality_algorithm.extract_decisions()
        if not decisions:
            return

        ts = TrainingSet.objects.create(job=self)
        for sample_id, label in decisions:
            if label == LABEL_BROKEN:
                log.info(
                    'Job %d: Skipped broken training sample %d.' % (self.id, sample_id)
                )
                continue
            sample = Sample.objects.get(id=sample_id)
            log.info(
                'Job %d: Added training sample %d %s.' % (self.id, sample_id, label)
            )
            TrainingSample.objects.create(
                set=ts,
                sample=sample,
                label=label,
            )

        for sample in self.sample_set.all().iterator():
            if sample.is_gold_sample():
                ts_sample, created = TrainingSample.objects.get_or_create(
                    set=ts,
                    sample=sample,
                )
                if not created:
                    log.info(
                        'Job %d: Overriden gold sample %d.' % (self.id, sample.id)
                    )
                ts_sample.label = sample.goldsample.label
                ts_sample.save()

        send_event(
            'EventTrainingSetCompleted',
            set_id=ts.id,
        )

    def start_btm(self, topic, description, no_of_urls):
        Job.objects.filter(id=self.id).update(
            btm_active=True,
            btm_to_gather=no_of_urls,
        )
        self.btm_active = True
        self.btm_to_gather = no_of_urls

        send_event(
            'EventBTMStarted',
            job_id=self.id,
            topic=topic,
            description=description,
            no_of_urls=no_of_urls,
        )

    def get_btm_status(self):
        """
            Returns a string representing job's BTM status.
        """
        # TODO: Fill this out
        return '---'

    def get_btm_verified_samples(self):
        """
            Returns list of samples verified by BTM to be added to training set.
        """
        # TODO: Proper query that returns a list of Sample objects.
        return []

    def get_btm_pending_samples(self):
        """
            Returns a list of samples that need to be added to the job by the
            owner.
        """
        # TODO: Proper query
        return [{
                'id': 0,
                'get_type': 'test',
                'url': 'test',
                'added_on': datetime.datetime.now(),
                'get_yes_probability': 100,
                'get_no_probability': 100,
                'get_broken_probability': 100,
                'get_yes_votes': 10,
                'get_no_votes': 10,
                'get_broken_votes': 10,
                'label': 'yes',
            }, {
                'id': 1,
                'get_type': 'test',
                'url': 'test2',
                'added_on': datetime.datetime.now(),
                'get_yes_probability': 100,
                'get_no_probability': 100,
                'get_broken_probability': 100,
                'get_yes_votes': 10,
                'get_no_votes': 10,
                'get_broken_votes': 10,
                'label': 'no',
            }
        ]

    def add_btm_verified_sample(self, sample):
        """
            Should add a BTM-verified sample to the job so it can be included
            in new training sets.
        """
        # TODO: Fill this out.
        return None

    def is_btm_finished(self):
        return (self.is_btm_active()
            and (self.get_btm_gathered() == self.get_btm_to_gather()))

    def is_btm_active(self):
        return self.btm_active

    def get_btm_to_gather(self):
        return self.btm_to_gather

    def get_btm_gathered(self):
        # TODO: Fill this. Should return a list of samples so that
        #       get_btm_gathered|length == number of samples that count towards
        #       BTM progress.
        #       Refer to OANNOTATOR-55
        return []

    def get_btm_progress(self):
        to_gather = self.get_btm_to_gather() or 1

        return round((100 * len(self.get_btm_gathered())) / to_gather, 2)

    def get_accepted_btm_samples(self):
        """
            Returns list of btm samples to add to training set.
        """

    def reclassify_samples(self):
        """
            Asynchronously reclassifies all samples.
        """
        for sample in self.sample_set.all().iterator():
            sample.reclassify()

    def has_new_votes(self):
        """
            Returns whether there are new votes in the job.
        """
        for sample in self.sample_set.iterator():
            if sample.workerqualityvote_set.filter(is_new=True).count():
                return True
        return False

    def get_link_with_title(self):
        return '<a href="%s">%s</a>' % (self.get_absolute_url(), self.title)

    def get_sample_gathering_url(self):
        """
            Returns the URL under which Own Workforce can submit new samples.
        """
        try:
            tag_job = self.tagasaurisjobs
            return tag_job.get_sample_gathering_url()
        except:
            return ''

    def stop_sample_gathering(self):
        """
            Stops underlying sample gathering job.
        """
        tag_job = self.tagasaurisjobs
        tag_job.sample_gathering_hit = ''
        tag_job.save()
        stop_job(tag_job.sample_gathering_key)
        return True

    def get_voting_url(self):
        """
            Returns the URL under which Own Workforce can vote on labels.
        """
        try:
            tag_job = self.tagasaurisjobs
            return tag_job.get_voting_url()
        except:
            return ''

    def stop_voting(self):
        """
            Stops underlying voting job.
        """
        tag_job = self.tagasaurisjobs
        tag_job.voting_hit = ''
        tag_job.save()
        stop_job(tag_job.voting_key)
        return True

    def get_classifier_performance(self):
        """
            Returns classifier performance as a dict with keys 'TPR', 'TNR',
            'AUC'.
        """
        performances = self.classifierperformance_set.all()
        ret = max(performances, key=(lambda x: x.date))
        return round(ret.value.get('AUC', 0), 2)

    def get_newest_votes(self, num=3):
        """
            Returns newest correct votes in the job.
        """
        from urlannotator.classification.models import (TrainingSet,
            TrainingSample)
        training_set = TrainingSet.objects.newest_for_job(job=self)
        samples = TrainingSample.objects.filter(
            set=training_set,
            label=LABEL_YES,
        ).order_by('-id')[:num]
        return samples

    def is_own_workforce(self):
        return self.data_source == JOB_SOURCE_OWN_WORKFORCE

    def get_status(self):
        return self.get_status_display()

    def is_draft(self):
        return self.status == JOB_STATUS_DRAFT

    def is_active(self):
        return self.status == JOB_STATUS_ACTIVE

    def activate(self):
        """
            Activates current job. Due to it's nature, this method REQUIRES
            synchronization outside.
        """
        if self.is_active():
            return
        self.status = JOB_STATUS_ACTIVE
        self.activated = now()
        self.save()
        send_event(
            "EventNewJobInitializationDone",
            job_id=self.id,
        )

    def initialize(self):
        self.status = JOB_STATUS_INIT
        self.remaining_urls = self.no_of_urls
        self.save()
        send_event('EventNewJobInitialization',
            job_id=self.id)

    def get_hours_spent(self, cache=False):
        """
            Returns number of hours workers have worked on this project
            altogether.

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        key = 'job-%d-hours-spent' % self.id
        mc = get_cache('memcache')
        val = mc.get(key)
        if val and cache:
            return val

        sum_res = WorkerJobAssociation.objects.filter(job=self).\
            aggregate(Sum('worked_hours'))
        sum_res = sum_res['worked_hours__sum']
        sum_res = sum_res if sum_res else 0

        mc.set(key, sum_res, 0)
        return sum_res

    def get_urls_collected(self, cache=False):
        """
            Returns number of urls collected (samples without gold samples).

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        key = 'job-%d-urls-collected' % self.id
        mc = get_cache('memcache')
        val = mc.get(key)
        if val and cache:
            return val

        samples = self.sample_set.all().select_related('goldsample').iterator()
        gold_samples = [gold['url'] for gold in self.gold_samples]

        collected = ifilter(lambda x: not x.is_gold_sample() and not x.url in gold_samples, samples)
        collected = sum(1 for _ in collected)

        mc.set(key, collected, 0)
        return collected

    def get_workers(self):
        """
            Returns workers associated with the job.
        """
        workers = [assoc.worker
            for assoc in WorkerJobAssociation.objects.filter(job=self)]
        return workers

    def get_no_of_workers(self):
        """
            Returns number of workers that have worked on this project.
        """
        return WorkerJobAssociation.objects.filter(job=self).count()

    def get_top_workers(self, num=3, cache=False):
        """
            Returns `num` top of workers.

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        key = 'job-%d-top-workers' % self.id
        mc = get_cache('memcache')
        val = mc.get(key)
        if val and cache:
            return val

        workers = self.get_workers()
        workers.sort(
            key=lambda w: -w.get_urls_collected_count_for_job(self)
        )

        workers = workers[:num]
        mc.set(key, workers, 0)
        return workers

    def get_cost(self, cache=False):
        """
            Returns amount of money the job has costed so far.

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        # FIXME: Add proper billing entries?
        return self.hourly_rate * self.get_hours_spent(cache=cache)

    def get_votes_gathered(self, cache=False):
        """
            Returns amount of votes gathered.

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        key = 'job-%d-votes-gathered' % self.id
        mc = get_cache('memcache')
        val = mc.get(key)
        if val and cache:
            return val

        samples = self.sample_set.all().iterator()
        count = 0
        for sample in samples:
            count += sample.workerqualityvote_set.filter(btm_vote=False).count()

        mc.set(key, count, 0)
        return count

    def get_progress(self, cache=False):
        """
            Returns actual progress (in percents) in the job.

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        return (self.get_progress_urls(cache=cache)
            + self.get_progress_votes(cache=cache)) / 2.0

    def get_progress_urls(self, cache=False):
        """
            Returns actual progress of urls collecting.

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        key = 'job-%d-progress-urls' % self.id
        mc = get_cache('memcache')
        val = mc.get(key)
        if val and cache:
            return val

        if not self.no_of_urls:
            return 100

        div = self.no_of_urls
        val = min((100 * self.get_urls_collected(cache=cache)) / div, 100)
        mc.set(key, val, 0)
        return val

    def get_progress_votes(self, cache=False):
        """
            Returns actual progress of votes collecting.

            Parameters:
            :param cache: - whether to use cache. If not or the cache has
                            expired, it will be updated.
        """
        key = 'job-%d-progress-votes' % self.id
        mc = get_cache('memcache')
        val = mc.get(key)
        if val and cache:
            return val

        count = self.sample_set.all().count() * 3
        got = self.get_votes_gathered(cache=cache)

        count = count or 1
        val = min((100 * got) / count, 100)
        mc.set(key, val, 0)
        return val

    def is_completed(self):
        return self.status == JOB_STATUS_COMPLETED

    def complete(self):
        self.status = JOB_STATUS_COMPLETED
        self.save()

    def is_stopped(self):
        return self.status == JOB_STATUS_STOPPED

    def stop(self):
        self.status = JOB_STATUS_STOPPED
        self.save()

    def is_initializing(self):
        return self.status == JOB_STATUS_INIT

    def set_flag(self, flag):
        with POSIXLock(name='job-%d-mutex' % self.id):
            self.initialization_status = F('initialization_status') | flag
            self.save()

            job = Job.objects.get(id=self.id)
            self.initialization_status = job.initialization_status

            if self.initialization_status == JOB_FLAGS_ALL:
                self.activate()
            elif (self.is_training_set_created()
                    and self.is_gold_samples_done()
                    and self.is_classifier_created()
                    and not self.gold_samples):
                # If we have no gold samples, activate without training
                # the classifier.
                self.activate()

    def unset_flag(self, flag):
        self.initialization_status = F('initialization_status') & (~flag)
        self.save()

        job = Job.objects.get(id=self.id)
        self.initialization_status = job.initialization_status

    def is_flag_set(self, flag):
        return self.initialization_status & flag != 0

    def set_training_set_created(self):
        self.set_flag(JOB_FLAGS_TRAINING_SET_CREATED)

    def is_training_set_created(self):
        return self.is_flag_set(JOB_FLAGS_TRAINING_SET_CREATED)

    def set_gold_samples_done(self):
        self.set_flag(JOB_FLAGS_GOLD_SAMPLES_DONE)
        send_event(
            'EventGoldSamplesDone',
            job_id=self.id,
        )

    def is_gold_samples_done(self):
        return self.is_flag_set(JOB_FLAGS_GOLD_SAMPLES_DONE)

    def set_classifier_created(self):
        self.set_flag(JOB_FLAGS_CLASSIFIER_CREATED)

    def is_classifier_created(self):
        return self.is_flag_set(JOB_FLAGS_CLASSIFIER_CREATED)

    def set_classifier_trained(self):
        self.set_flag(JOB_FLAGS_CLASSIFIER_TRAINED)

    def unset_classifier_trained(self):
        self.unset_flag(JOB_FLAGS_CLASSIFIER_TRAINED)

    def is_classifier_trained(self):
        return self.is_flag_set(JOB_FLAGS_CLASSIFIER_TRAINED)

    @staticmethod
    def is_odesk_required_for_source(source):
        return int(source) != 1

# Sample source types breakdown:
# owner - Sample created by the job creator. source_val is empty.
SAMPLE_SOURCE_OWNER = 'owner'
SAMPLE_TAGASAURIS_WORKER = 'tagasauris_worker'


class SampleManager(models.Manager):

    def _domain(self, url):
        return urlparse.urlparse(url).hostname

    def _sanitize(self, args, kwargs):
        """
            Sample data sanitization.
        """
        url = kwargs.get('url', '')

        # Add missing schema. Defaults to http://
        if url:
            result = urlparse.urlsplit(url)
            if not result.scheme:
                kwargs['url'] = 'http://%s' % url

            domain = self._domain(kwargs['url'])
            kwargs['domain'] = domain

    def _create_sample(self, *args, **kwargs):

        return send_event(
            'EventNewRawSample',
            *args, **kwargs
        )

    def create_by_owner(self, *args, **kwargs):
        '''
            Asynchronously creates a new sample with owner as a source.
        '''
        self._sanitize(args, kwargs)
        kwargs['source_type'] = SAMPLE_SOURCE_OWNER

        return self._create_sample(*args, **kwargs)

    def create_by_worker(self, *args, **kwargs):
        '''
            Asynchronously creates a new sample with tagasauris worker as a
            source.
        '''
        self._sanitize(args, kwargs)
        kwargs['source_type'] = SAMPLE_TAGASAURIS_WORKER

        # Add worker-job association.
        worker, created = Worker.objects.get_or_create_tagasauris(
            worker_id=kwargs['source_val']
        )
        job = Job.objects.get(id=kwargs['job_id'])

        WorkerJobAssociation.objects.associate(
            job=job,
            worker=worker,
        )

        return self._create_sample(*args, **kwargs)

    def create_by_btm(self, *args, **kwargs):
        '''
            Asynchronously creates a new sample with tagasauris worker as a
            source.
            It will be BTM (Beat The Machine) sample so it wont get into
            voting unless vote_sample parameter will be set.
        '''
        self._sanitize(args, kwargs)
        kwargs['source_type'] = SAMPLE_TAGASAURIS_WORKER
        kwargs['vote_sample'] = False
        kwargs['btm_sample'] = True
        kwargs['training'] = False

        # Add worker-job association.
        worker, created = Worker.objects.get_or_create_tagasauris(
            worker_id=kwargs['source_val']
        )
        job = Job.objects.get(id=kwargs['job_id'])

        WorkerJobAssociation.objects.associate(
            job=job,
            worker=worker,
        )

        return self._create_sample(*args, **kwargs)

    def by_worker(self, source_type, source_val, **kwargs):
        """
            Returns samples done by the worker.
        """
        return self.filter(source_type=source_type, source_val=source_val)


class Sample(models.Model):
    """
        A sample used to classify and verify.
    """
    job = models.ForeignKey(Job)
    url = models.URLField()
    domain = models.CharField(max_length=100, blank=False)
    text = models.TextField()
    screenshot = models.URLField()
    source_type = models.CharField(max_length=100, blank=False)
    source_val = models.CharField(max_length=100, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    btm_sample = models.BooleanField(default=False)
    vote_sample = models.BooleanField(default=True)
    training = models.BooleanField(default=True)

    objects = SampleManager()

    class Meta:
        unique_together = ('job', 'url')

    @staticmethod
    def get_worker(source_type, source_val):
        """
            Returns a worker that corresponds to given (`source_type`,
            `source_val`) pair.
        """
        if source_type == SAMPLE_SOURCE_OWNER:
            # If the sample's creator is owner, ignore source worker.
            return None
        elif source_type == SAMPLE_TAGASAURIS_WORKER:
            return Worker.objects.get_tagasauris(worker_id=source_val)

    def get_classified_label(self):
        class_set = self.classifiedsample_set.all().order_by('-id')
        if class_set:
            return class_set[0].label
        return None

    def reclassify(self):
        """
            Asynchronously reclassifies given `sample`.
        """
        # Possible loop imports here
        from urlannotator.classification.models import ClassifiedSample
        ClassifiedSample.objects.create_by_owner(
            job=self.job,
            url=self.url,
            sample=self,
        )

    def get_source_worker(self):
        """
            Returns a worker that has sent this sample.
        """
        return self.get_worker(
            source_type=self.source_type,
            source_val=self.source_val,
        )

    def get_screenshot_key(self):
        """
            Returns sample's key used to authenticate thumbnail request in
            imagescale.
        """
        algorithm = hashlib.new(imagescale2.HASHING_ALGORITHM)
        algorithm.update(imagescale2.SALT)
        algorithm.update(self.screenshot)
        return algorithm.hexdigest()

    def get_thumbnail(self, width=60, height=60):
        """
            Returns a thumbnail from sample's screenshot fit to given size.
        """
        params = {
            'width': width,
            'height': height,
            'url': self.screenshot,
            'key': self.get_screenshot_key(),
        }
        r = requests.get('http://' + settings.IMAGESCALE_URL, params=params)
        return r.content

    def get_small_thumbnail_url(self):
        """
            Returns url which serves sample's small thumbnail.
        """
        return self.get_thumbnail_url('small')

    def get_small_thumbnail(self):
        """
            Returns a small (60x60) thumbnail to use in samples list, etc.
        """
        return self.get_thumbnail(width=60, height=60)

    def get_thumbnail_url(self, size):
        """
            Returns url which serves sample's thumbnail in given size.

            :param size: one of `size`, `large`
        """
        return reverse('sample_thumbnail', args=[self.id, size])

    def get_large_thumbnail_url(self):
        """
            Returns url which serves sample's small thumbnail.
        """
        return self.get_thumbnail_url('large')

    def get_large_thumbnail(self):
        """
            Returns a large (300x300) thumbnail to use as screenshot's preview.
        """
        return self.get_thumbnail(width=300, height=300)

    def is_finished(self):
        """
            Whether the sample's creation has been finished.
        """
        return self.text and self.screenshot

    def get_workers(self):
        """
            Returns workers that have sent this sample (url).
        """
        workers = set()
        for cs in self.classifiedsample_set.all().iterator():
            worker = cs.get_source_worker()
            if worker and worker.can_show_to_user():
                workers.add(worker)
        return workers

    def get_yes_votes(self):
        """
            Returns amount of YES votes received by this sample.
        """
        votes = self.workerqualityvote_set.all()
        num = sum(1 for _ in ifilter(lambda x: x.label == LABEL_YES, votes))
        return num

    def get_no_votes(self):
        """
            Returns amount of NO votes received by this sample.
        """
        votes = self.workerqualityvote_set.all()
        num = sum(1 for _ in ifilter(lambda x: x.label == LABEL_NO, votes))
        return num

    def get_broken_votes(self):
        """
            Returns amount of BROKEN votes received by this sample.
        """
        votes = self.workerqualityvote_set.all()
        num = sum(1 for _ in ifilter(lambda x: x.label == LABEL_BROKEN, votes))
        return num

    def get_yes_probability(self):
        """
            Returns probability of YES label on this sample, that is the
            percentage from the most recent classification.
        """
        cs_set = self.classifiedsample_set.all()
        if not cs_set:
            return 0

        cs = max(cs_set, key=(lambda x: x.id))
        yes_prob = cs.get_yes_probability()
        return yes_prob

    def get_no_probability(self):
        """
            Returns probability of NO label on this sample, that is the
            percentage from the most recent classification.
        """
        cs_set = self.classifiedsample_set.all()
        if not cs_set:
            return 0

        cs = max(cs_set, key=(lambda x: x.id))
        no_prob = cs.get_no_probability()
        return no_prob

    def get_broken_probability(self):
        """
            Returns probability of BROKEN label on this sample, that is the
            percentage from the most recent classification.
        """
        cs_set = self.classifiedsample_set.all()
        if not cs_set:
            return 0

        cs = max(cs_set, key=(lambda x: x.id))
        broken_prob = cs.get_broken_probability()
        return broken_prob

    def is_classified(self):
        """
            Returns whether this sample has been classified at least once.
        """
        # Check if we have been voted down as BROKEN
        from urlannotator.classification.models import (TrainingSet,
            TrainingSample)
        ts = TrainingSet.objects.newest_for_job(self.job)
        count = TrainingSample.objects.filter(
            sample=self,
            set=ts,
        ).count()

        # We are not adding broken samples to training sets
        if not count:
            return False

        yes_prob = self.get_yes_probability()
        no_prob = self.get_no_probability()

        return yes_prob or no_prob

    def is_gold_sample(self):
        try:
            return self.goldsample is not None
        except:
            return False

    @classmethod
    def sanitize_url(cls, url):
        kwargs = {'url': url}
        cls.objects._sanitize(None, kwargs)
        return kwargs['url']


# Worker types breakdown:
# odesk - worker from odesk. External id points to user's odesk id.
# internal - worker registered in our system. External id is the user's id.
# tagasauris - worker provided by tagasauris.
WORKER_TYPE_ODESK = 0
WORKER_TYPE_INTERNAL = 1
WORKER_TYPE_TAGASAURIS = 2

WORKER_TYPES = (
    (WORKER_TYPE_ODESK, 'oDesk'),
    (WORKER_TYPE_INTERNAL, 'internal'),
    (WORKER_TYPE_TAGASAURIS, 'tagasauris'),
)

worker_type_to_sample_source = {
    WORKER_TYPE_TAGASAURIS: SAMPLE_TAGASAURIS_WORKER,
    WORKER_TYPE_INTERNAL: SAMPLE_SOURCE_OWNER,
    WORKER_TYPE_ODESK: SAMPLE_SOURCE_OWNER,
}


class WorkerManager(models.Manager):
    def create_odesk(self, *args, **kwargs):
        kwargs['worker_type'] = WORKER_TYPE_ODESK

        return self.create(**kwargs)

    def create_tagasauris(self, *args, **kwargs):
        kwargs['worker_type'] = WORKER_TYPE_TAGASAURIS

        return self.create(**kwargs)

    def create_internal(self, *args, **kwargs):
        kwargs['worker_type'] = WORKER_TYPE_INTERNAL

        return self.create(**kwargs)

    def get_tagasauris(self, worker_id):
        return self.get(
            worker_type=WORKER_TYPE_TAGASAURIS,
            external_id=worker_id,
        )

    def get_or_create_tagasauris(self, worker_id):
        """
            Gets or creates Tagasauris worker with given id.
            Returns a 2-tuple (object, created):
            `worker` - the Worker object
            `created` - whether the object has been created or not.
        """
        return self.get_or_create(
            worker_type=WORKER_TYPE_TAGASAURIS,
            external_id=worker_id,
        )

    def get_odesk(self, external_id):
        return self.get(
            external_id=external_id,
            worker_type=WORKER_TYPE_ODESK,
        )


class Worker(models.Model):
    """
        Represents the worker who has completed a HIT.
    """
    external_id = models.CharField(max_length=100)
    worker_type = models.IntegerField(max_length=100, choices=WORKER_TYPES)

    objects = WorkerManager()

    def __unicode__(self):
        return self.get_name()

    def can_show_to_user(self):
        return self.worker_type != WORKER_TYPE_INTERNAL

    def get_name(self):
        """
            Returns worker's name.
        """
        if self.worker_type == WORKER_TYPE_ODESK:
            client = odesk.Client(
                settings.ODESK_SERVER_KEY,
                settings.ODESK_SERVER_SECRET,
                oauth_access_token=settings.ODESK_SERVER_TOKEN_KEY,
                oauth_access_token_secret=settings.ODESK_SERVER_TOKEN_SECRET,
                auth='oauth',
            )
            r = client.provider.get_provider(self.external_id)
            return r['dev_full_name']

        # if self.worker_type == WORKER_TYPE_TAGASAURIS:
        #     tc = make_tagapi_client()
        #     worker_info = tc.get_worker(worker_id=self.external_id)
        #     return worker_info['name']

        return 'Worker %d' % self.id

    def get_urls_collected_count_for_job(self, job):
        """
            Returns count of urls collected by worker for given job.
        """
        return len(self.get_urls_collected_for_job(job))

    def get_urls_collected_for_job(self, job):
        """
            Returns urls collected by given worker for given job.
        """
        # Importing here due to loop imports higher in the scope.
        from urlannotator.classification.models import ClassifiedSample
        return ClassifiedSample.objects.filter(
            job=job,
            source_type=worker_type_to_sample_source[self.worker_type],
            source_val=self.external_id)

    def get_links_collected(self):
        """ Returns number of links collected.
        """
        # Importing here due to loop imports higher in the scope.
        from urlannotator.classification.models import ClassifiedSample
        return ClassifiedSample.objects.filter(
            source_val=self.external_id,
            source_type=worker_type_to_sample_source[self.worker_type]
        ).count()

    def log_time_for_job(self, job, time):
        """
            Logs time worker has worker for given job for.

            :param time: a Decimal instance, or any other type that a Decimal
                         can be constructed from.
        """
        assoc = WorkerJobAssociation.objects.filter(job=job, worker=self)
        assoc.update(worked_hours=F('worked_hours') + time)

    def get_hours_spent_for_job(self, job):
        """
            Returns hours spent by given worker for given job.
        """
        try:
            assoc = WorkerJobAssociation.objects.get(job=job, worker=self)
            return assoc.worked_hours
        except WorkerJobAssociation.DoesNotExist:
            return 0

    def get_votes_added_count_for_job(self, job):
        """
            Returns count of votes added by given worker for given job.
        """
        return sum(1 for vote in self.get_votes_added_for_job(job))

    def get_votes_added_for_job(self, job):
        """
            Returns votes added by given worker for given job.
        """
        return ifilter(
            lambda x: x.sample.job == job and x.worker == self,
            self.workerqualityvote_set.all()
        )

    def get_earned_for_job(self, job):
        """
            Returns total amount of money earned by the given worker during
            given job.
        """
        # FIXME: Proper billing query.
        return 0

    def get_job_start_time(self, job):
        '''
            Returns the time the worker started to work on the job at.
        '''
        try:
            assoc = WorkerJobAssociation.objects.get(job=job, worker=self)
        except WorkerJobAssociation.DoesNotExist:
            return datetime.datetime.now()

        return assoc.started_on

    def get_estimated_quality_for_job(self, job):
        """
            Retuns worker's estimated quality for given job.
        """
        return self.workerjobassociation_set.get(job=job).get_estimated_quality()


class WorkerJobManager(models.Manager):
    def associate(self, job, worker):
        exists = self.filter(job=job, worker=worker).count()
        if not exists:
            self.create(job=job, worker=worker)


class WorkerJobAssociation(models.Model):
    """
        Holds worker associations with jobs they have participated in.
    """
    job = models.ForeignKey(Job)
    worker = models.ForeignKey(Worker)
    started_on = models.DateTimeField(auto_now_add=True)
    worked_hours = models.DecimalField(default=0, decimal_places=2,
        max_digits=10)
    data = JSONField(default='{}')

    objects = WorkerJobManager()

    def get_estimated_quality(self):
        return self.data.get('estimated_quality', 0)


class GoldSample(models.Model):
    """
        Sample uploaded by project owner. It is already classified and is used
        to train classifier.
    """
    sample = models.OneToOneField(Sample)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES)


class ProgressManager(models.Manager):
    def latest_for_job(self, job):
        """
            Returns progress statistic for given job.
        """
        els = super(ProgressManager, self).get_query_set().filter(job=job).\
            order_by('-date')
        if not els.count():
            return None

        return els[0]


class ProgressStatistics(models.Model):
    """
        Keeps track of job progress per hour.
    """
    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    value = models.IntegerField(default=0)
    delta = models.IntegerField(default=0)

    objects = ProgressManager()


class SpentManager(models.Manager):
    def latest_for_job(self, job):
        """
            Returns spent statistic for given job.
        """
        els = super(SpentManager, self).get_query_set().filter(job=job).\
            order_by('-date')
        if not els.count():
            return None

        return els[0]


class SpentStatistics(models.Model):
    """
        Keeps track of job spent amount per hour.
    """
    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    value = models.IntegerField(default=0)
    delta = models.IntegerField(default=0)

    objects = SpentManager()


class URLStatManager(models.Manager):
    def latest_for_job(self, job):
        """
            Returns url collected statistic for given job.
        """
        els = super(URLStatManager, self).get_query_set().filter(job=job).\
            order_by('-date')
        if not els.count():
            return None

        return els[0]


class URLStatistics(models.Model):
    """
        Keeps track of urls collected for a job per hour.
    """
    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    value = models.IntegerField(default=0)
    delta = models.IntegerField(default=0)

    objects = URLStatManager()


class VotesStatManager(models.Manager):
    def latest_for_job(self, job):
        """
            Returns votes collected statistic for given job.
        """
        els = super(VotesStatManager, self).get_query_set().filter(job=job).\
            order_by('-date')
        if not els.count():
            return None

        return els[0]


class VotesStatistics(models.Model):
    """
        Keeps track of votes gathered for a job per hour.
    """
    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    value = models.IntegerField(default=0)
    delta = models.IntegerField(default=0)

    objects = VotesStatManager()


class LinksStatManager(models.Manager):
    def latest_for_worker(self, worker):
        """ Returns url collected statistic for given worker.
        """
        els = super(LinksStatManager, self).get_query_set().filter(
            worker=worker).order_by('-date')
        if not els.count():
            return None

        return els[0]


class LinksStatistics(models.Model):
    """ Keeps track of urls collected for worker per day.
    """
    worker = models.ForeignKey(Worker)
    date = models.DateTimeField(auto_now_add=True)
    value = models.IntegerField(default=0)
    delta = models.IntegerField(default=0)

    objects = LinksStatManager()


def create_stats(sender, instance, created, **kwargs):
    """
        Creates a brand new statistics' entry for new job.
    """
    if created:
        ProgressStatistics.objects.create(job=instance, value=0)
        SpentStatistics.objects.create(job=instance, value=0)
        URLStatistics.objects.create(job=instance, value=0)
        VotesStatistics.objects.create(job=instance, value=0)

post_save.connect(create_stats, sender=Job)


class FillSample(models.Model):
    """
        Contains a link to a webpage that will be added to a job as a negative
        gold sample.

        Amount of samples added is equal to total number of urls to find.
    """
    url = models.URLField(primary_key=True)
