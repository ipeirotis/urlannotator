from celery import task, Task, registry
from factories import SampleFactory, JobFactory

from urlannotator.classification.models import TrainingSample, TrainingSet
from urlannotator.main.models import GoldSample
from urlannotator.flow_control import send_event
from urlannotator.tools.synchronization import ContextPOSIXLock


@task()
class EventRawSampleManager(Task):
    """
        Manage factories to handle creation of new samples.
    """

    def __init__(self):
        self.factory = SampleFactory()

    def run(self, *args, **kwargs):
        self.factory.new_sample(*args, **kwargs)

new_raw_sample_task = registry.tasks[EventRawSampleManager.name]


@task()
class JobFactoryManager(Task):
    """
        Manages factories handling Job initialization (from db entry).
    """

    def __init__(self):
        self.factory = JobFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_job(*args, **kwargs)

new_job_task = registry.tasks[JobFactoryManager.name]


@task()
class GoldSamplesMonitor(Task):
    """
        Monitors gold samples creation, and issues classificator training
        if a complete set of gold samples has been prepared.
    """

    def __init__(self):
        self.samples = []

    def run(self, gold_id, *args, **kwargs):
        # FIXME: Mock
        self.samples.append(gold_id)

        gold_sample = GoldSample.objects.get(id=gold_id)
        job = gold_sample.sample.job

        # If training set is not prepared, retry later
        if not job.is_training_set_created():
            registry.tasks[GoldSamplesMonitor.name].retry(countdown=30)

        training_set = TrainingSet.objects.newest_for_job(job)
        TrainingSample(
            set=training_set,
            sample=gold_sample.sample,
            label=gold_sample.label
        ).save()

        lock_key = 'TrainingSampleLock-%d' % job.id
        # FIXME: Correct event name?
        # Send training set completed event. Used here as we are certain no
        # new samples will come in the mean time. In general, you can't
        # assume that!
        with ContextPOSIXLock(name=lock_key):
            if not job.is_gold_samples_done():
                all_golds = len(job.gold_samples)
                current_golds = training_set.training_samples.count()
                if all_golds == current_golds:
                    job.set_gold_samples_done()
                    send_event(
                        "EventTrainingSetCompleted",
                        training_set.id
                    )

new_gold_sample_task = registry.tasks[GoldSamplesMonitor.name]

FLOW_DEFINITIONS = [
    (r'^EventNewRawSample$', new_raw_sample_task),
    (r'^EventNewJobInitialization$', new_job_task),
    (r'^EventNewGoldSample$', new_gold_sample_task),
]
