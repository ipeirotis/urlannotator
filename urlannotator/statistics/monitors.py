import datetime

from django.utils.timezone import now

from urlannotator.main.models import Job, Worker


class StatsMonitor(object):
    """ Every *_MONITOR_INTERVAL queries for objects requiring statistics
        recomputation and does it.
        Interval argument has to be an instance of datetime.timedelta.
        Requires model class's manager to implement 'latest_for_*(obj)',
        where obj is an instance of obj model.
        Inheriting classes MUST define get_value(obj) method.
        This class is written to be Mixin-able with celery.Task.
    """
    def __init__(self, cls, interval=datetime.timedelta(hours=1), *args,
            **kwargs):
        self.interval = interval
        self.model_cls = cls
        super(StatsMonitor, self).__init__(*args, **kwargs)

    def handle(self, obj_set):
        """ Handles performing periodic tasks on computed obj set. obj set is
            a list of 2-tuples (obj, old statistic entry).
        """
        new_stats = []
        for obj, old_entry in obj_set:
            old_value = old_entry.value
            new_value = self.get_value(obj)
            delta = new_value - old_value
            new_stats.append(self.new_stats(obj, new_value, delta))

        if new_stats:
            self.model_cls.objects.bulk_create(new_stats)

    def get_value(self, obj):
        """ Gets specific statistic.
        """
        return 0

    def get_latest(self, obj):
        """ Gets latest statistic entry.
        """
        return None

    def get_objects(self):
        """ Gets objects for statistics gather.
        """
        return []

    def new_stats(self, obj, value, delta):
        """ Creates new instance of stats class.
        """
        return None

    def run(self, interval=datetime.timedelta(hours=1), *args, **kwargs):
        """
            Scans all active objects for the ones that require stats
            recomputation. Does it in an infinite loop, after
            settings.*_MONITOR_INTERVAL seconds from previous loop.
        """
        objects = self.get_objects()
        to_handle = []
        for obj in objects:
            latest = self.get_latest(obj)
            if not latest:
                continue
            handle_time = latest.date + interval
            if handle_time <= now():
                to_handle.append((obj, latest))

        if to_handle:
            self.handle(to_handle)


class JobMonitor(StatsMonitor):

    def get_latest(self, obj):
        return self.model_cls.objects.latest_for_job(obj)

    def get_objects(self):
        return Job.objects.get_active()

    def new_stats(self, obj, value, delta):
        return Job(
            job=obj,
            value=value,
            delta=delta
        )


class WorkerMonitor(StatsMonitor):
    """ Similar to JobMonitor.
    """

    def get_latest(self, obj):
        return self.model_cls.objects.latest_for_worker(obj)

    def get_objects(self):
        return Worker.objects.all()

    def new_stats(self, obj, value, delta):
        return Worker(
            worker=obj,
            value=value,
            delta=delta
        )
