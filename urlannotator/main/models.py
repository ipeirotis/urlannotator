import datetime
# import odesk

from tastypie.models import create_api_key

from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.timezone import now
from tenclouds.django.jsonfield.fields import JSONField

from urlannotator.flow_control import send_event
from urlannotator.tools.synchronization import POSIXLock

LABEL_CHOICES = (('Yes', 'Yes'), ('No', 'No'), ('Broken', 'Broken'))


class Account(models.Model):
    """
        Model representing additional user data. Used as user profile.
    """
    user = models.ForeignKey(User)
    activation_key = models.CharField(default='', max_length=100)
    email_registered = models.BooleanField(default=False)
    odesk_key = models.CharField(default='', max_length=100)
    odesk_uid = models.CharField(default='', max_length=100)
    full_name = models.CharField(default='', max_length=100)
    alerts = models.BooleanField(default=False)
    worker_entry = models.ForeignKey('Worker', null=True, blank=True)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
post_save.connect(create_api_key, sender=User)

JOB_BASIC_DATA_SOURCE_CHOICES = ((1, 'Own workforce'),)
JOB_DATA_SOURCE_CHOICES = JOB_BASIC_DATA_SOURCE_CHOICES + \
                          ((0, 'Odesk free'), (2, 'Odesk paid'))
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
        send_event('EventNewJobInitialization', job.id)
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
    account = models.ForeignKey(Account, related_name='project')
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
    gold_samples = JSONField()
    classify_urls = JSONField()
    budget = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    remaining_urls = models.PositiveIntegerField(default=0)
    collected_urls = models.PositiveIntegerField(default=0)
    initialization_status = models.IntegerField(default=0)
    activated = models.DateTimeField(auto_now_add=True)

    objects = JobManager()

    @models.permalink
    def get_absolute_url(self):
        return ('project_view', (), {
            'id': self.id,
        })

    def get_status(self):
        return JOB_STATUS_CHOICES[self.status][1]

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
        send_event('EventNewJobInitialization', self.id)

    def get_hours_spent(self):
        """
            Returns number of hours workers have worked on this project
            altogether.
        """
        # FIXME: Returns number of hours since project activation
        delta = now() - self.activated
        return int(delta.total_seconds() / 3600)

    def get_urls_collected(self):
        """
            Returns number of urls collected.
        """
        # FIXME: Returns number of urls gathered. Should be number of urls
        #        that has gone through validation and are accepted.
        return self.no_of_urls - self.remaining_urls

    def get_no_of_workers(self):
        """
            Returns number of workers that have worked on this project.
        """
        # FIXME: Returns number of all workers.
        return Worker.objects.all().count()

    def get_cost(self):
        """
            Returns amount of money the job has costed so far.
        """
        # FIXME: Add proper billing entries?
        return self.hourly_rate * self.get_hours_spent()

    def get_progress(self):
        """
            Returns actual progress (in percents) in the job.
        """
        # FIXME: Is it proper way of getting progress?
        div = self.no_of_urls or 1
        return self.get_urls_collected() / div * 100

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
SAMPLE_TAGASAURIS_WORKER = 'owner'


class SampleManager(models.Manager):
    def create_by_owner(self, *args, **kwargs):
        '''
            Asynchronously creates a new sample with owner as a source.
        '''
        if 'source_type' in kwargs:
            kwargs.pop('source_type')

        return send_event(
            'EventNewRawSample',
            source_type=SAMPLE_SOURCE_OWNER,
            *args, **kwargs
        )

    def create_by_worker(self, *args, **kwargs):
        '''
            Asynchronously creates a new sample with tagasauris worker as a
            source.
        '''
        if 'source_type' in kwargs:
            kwargs.pop('source_type')

        return send_event(
            'EventNewRawSample',
            source_type=SAMPLE_TAGASAURIS_WORKER,
            *args, **kwargs
        )


class Sample(models.Model):
    """
        A sample used to classify and verify.
    """
    job = models.ForeignKey(Job)
    url = models.URLField()
    text = models.TextField()
    screenshot = models.URLField()
    source_type = models.CharField(max_length=100, blank=False)
    source_val = models.CharField(max_length=100, blank=True, null=True)
    added_on = models.DateField(auto_now_add=True)

    objects = SampleManager()

    class Meta:
        unique_together = ('job', 'url')

    def get_source_worker(self):
        '''
            Returns a worker that has sent this sample.
        '''
        # FIXME: Add support for more sources. Fix returned type for owner.
        #        Should be of Worker type.
        if self.source_type == SAMPLE_SOURCE_OWNER:
            cipher = self.job.account.odesk_uid
            try:
                worker = Worker.objects.get(external_id=cipher)
                return worker
            except Worker.DoesNotExist:
                return None

    def get_workers(self):
        """
            Returns workers that have sent this sample (url).
        """
        #  FIXME: Support for multiple workers sending the same url.
        return [self.source_type]

    def get_yes_votes(self):
        """
            Returns amount of YES votes received by this sample.
        """
        # FIXME: Actual votes.
        return 0

    def get_no_votes(self):
        """
            Returns amount of NO votes received by this sample.
        """
        # FIXME: Actual votes.
        return 0

    def get_broken_votes(self):
        """
            Returns amount of BROKEN votes received by this sample.
        """
        # FIXME: Actual votes.
        return 0

    def get_yes_probability(self):
        """
            Returns probability of YES label on this sample.
        """
        # TODO: More meaningful probability query? Currently most recent one.
        cs_set = self.classifiedsample_set.all()
        max_id = -1
        cs = None
        yes_prob = 0
        for cs_it in cs_set:
            if cs_it.id > max_id:
                max_id = cs_it.id
                cs = cs_it
        if cs:
            yes_prob = cs.label_probability['Yes']
        return yes_prob * 100

    def get_no_probability(self):
        """
            Returns probability of NO label on this sample.
        """
        # TODO: More meaningful probability query? Currently most recent one.
        cs_set = self.classifiedsample_set.all()
        max_id = -1
        cs = None
        no_prob = 0
        for cs_it in cs_set:
            if cs_it.id > max_id:
                max_id = cs_it.id
                cs = cs_it
        if cs:
            no_prob = cs.label_probability['No']
        return no_prob * 100

# --vote--
# label
# sample
# worker
# is_valid

# Worker types breakdown:
# odesk - worker from odesk. External id points to user's odesk id.

WORKER_TYPE_ODESK = 0

WORKER_TYPES = (
    (WORKER_TYPE_ODESK, 'oDesk'),
)


class WorkerManager(models.Manager):
    def create_odesk(self, *args, **kwargs):
        if 'worker_type' in kwargs:
            kwargs.pop('worker_type')

        return self.create(
            worker_type=WORKER_TYPE_ODESK,
            **kwargs
        )


class Worker(models.Model):
    """
        Represents the worker who has completed a HIT.
    """
    external_id = models.CharField(max_length=100)
    worker_type = models.IntegerField(max_length=100, choices=WORKER_TYPES)
    estimated_quality = models.DecimalField(default=0, decimal_places=5,
        max_digits=7)

    objects = WorkerManager()

    def get_name_as(self, requesting_user):
        """
            Returns worker's name. Uses requesting_user's ceredentials if
            necessary.
        """
        # FIXME: Uncomment when proper odesk external id handling is done

        # if self.worker_type == WORKER_TYPE_ODESK:
        #     client = odesk.Client(settings.ODESK_CLIENT_ID,
        #         settings.ODESK_CLIENT_SECRET,
        #         requesting_user.get_profile().odesk_key)
        #     r = client.provider.get_provider('~~3f19de366cb49c91')
        #     return r['dev_full_name']
        return 'Temp Name %d' % self.id

    def get_links_collected_for_job(self, job):
        """
            Returns links collected by given worker for given job.
        """
        # FIXME: Actual links collected query
        s = Sample.objects.filter(job=job)
        return s

    def get_hours_spent_for_job(self, job):
        """
            Returns hours spent by given worker for given job.
        """
        # FIXME: Proper time tracking. Now returns 0.
        return 0

    def get_votes_added_for_job(self, job):
        """
            Returns votes added by given worker for given job.
        """
        # FIXME: Proper votes query. Now returns empty set.
        return []

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
        return datetime.datetime.now()


class TemporarySample(models.Model):
    """
        Temporary sample used inbetween creating the real sample by processes
        responsible for each part.
    """
    text = models.TextField()
    screenshot = models.URLField()
    url = models.URLField()


class GoldSample(models.Model):
    """
        Sample uploaded by project owner. It is already classified and is used
        to train classifier.
    """
    sample = models.ForeignKey(Sample)
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


def create_stats(sender, instance, created, **kwargs):
    """
        Creates a brand new statistics' entry for new job.
    """
    if created:
        ProgressStatistics.objects.create(job=instance, value=0)
        SpentStatistics.objects.create(job=instance, value=0)
        URLStatistics.objects.create(job=instance, value=0)

post_save.connect(create_stats, sender=Job)
