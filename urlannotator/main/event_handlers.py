from celery import task, Task, registry
from factories import SampleFactory, JobFactory

from urlannotator.classification.models import TrainingSample, TrainingSet
from urlannotator.main.models import GoldSample, LABEL_BROKEN, Job
from urlannotator.flow_control import send_event
from urlannotator.tools.synchronization import POSIXLock


@task(ignore_result=True)
class EventRawSampleManager(Task):
    """
        Manage factories to handle creation of new samples.
    """

    def __init__(self):
        self.factory = SampleFactory()

    def run(self, *args, **kwargs):
        self.factory.new_sample(*args, **kwargs)

new_raw_sample_task = registry.tasks[EventRawSampleManager.name]


@task(ignore_result=True)
class JobFactoryManager(Task):
    """
        Manages factories handling Job initialization (from db entry).
    """

    def __init__(self):
        self.factory = JobFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_job(*args, **kwargs)

new_job_task = registry.tasks[JobFactoryManager.name]


@task(ignore_result=True)
class GoldSamplesMonitor(Task):
    """
        Monitors gold samples creation, and issues classificator training
        if a complete set of gold samples has been prepared.
    """
    def run(self, gold_id, *args, **kwargs):
        gold_sample = GoldSample.objects.get(id=gold_id)
        job = gold_sample.sample.job

        # If training set is not prepared, retry later
        if not job.is_training_set_created():
            registry.tasks[GoldSamplesMonitor.name].retry(countdown=30)

        if gold_sample.label != LABEL_BROKEN:
            training_set = TrainingSet.objects.newest_for_job(job)
            TrainingSample.objects.create(
                set=training_set,
                sample=gold_sample.sample,
                label=gold_sample.label
            )

        lock_key = 'TrainingSampleLock-%d' % job.id
        # Send training set completed event. Used here as we are certain no
        # new samples will come in the mean time. In general, you can't
        # assume that!
        with POSIXLock(name=lock_key):
            if not job.is_gold_samples_done():
                all_golds = len(job.gold_samples)
                current_golds = training_set.training_samples.count()
                if all_golds == current_golds:
                    job.set_gold_samples_done()
                    send_event(
                        "EventTrainingSetCompleted",
                        set_id=training_set.id,
                        job_id=job.id
                    )

new_gold_sample_task = registry.tasks[GoldSamplesMonitor.name]


@task(ignore_result=True)
def update_job_urls_gathered(job_id, sample_id):
    job = Job.objects.get(id=job_id)

    # A sample has been created.
    job.get_progress_urls(cache=False)
    # If it was created by a worker - update top workers too.
    job.get_top_workers(cache=False)
    job.get_display_samples(cache=False)


@task(ignore_result=True)
def update_job_newest_votes(job_id, set_id):
    job = Job.objects.get(id=job_id)
    job.get_newest_votes(cache=False)


FLOW_DEFINITIONS = [
    (r'^EventNewRawSample$', new_raw_sample_task),
    (r'^EventNewJobInitialization$', new_job_task),
    (r'^EventNewGoldSample$', new_gold_sample_task),
    (r'^EventNewSample$', update_job_urls_gathered),
    (r'^EventTrainingSetCompleted$', update_job_newest_votes),
]
