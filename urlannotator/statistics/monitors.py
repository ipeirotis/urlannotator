import datetime

from urlannotator.main.models import Job, Worker, WorkerJobAssociation


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
        for obj in obj_set:
            new_value = self.get_value(obj)
            new_stats.append(self.new_stats(obj, new_value))

        if new_stats:
            self.model_cls.objects.bulk_create(new_stats)
            self.after_handle(obj_set)

    def get_value(self, obj):
        """ Gets specific statistic.
        """
        return 0

    def get_latest(self, obj):
        """ Gets latest statistic entry.
        """
        return None

    def after_handle(self, obj_set):
        """ Handle fired after new stats are created.
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
            recomputation.
        """
        self.handle(self.get_objects())


class JobMonitor(StatsMonitor):

    def get_objects(self):
        return Job.objects.get_active()

    def new_stats(self, obj, value):
        return self.model_cls(
            job=obj,
            value=value,
        )


class WorkerJobMonitor(StatsMonitor):

    def get_objects(self):
        return WorkerJobAssociation.objects.filter(
            job__in=Job.objects.get_active())

    def new_stats(self, obj, value):
        return self.model_cls(
            job=obj.job,
            worker=obj.worker,
            value=value,
        )


class WorkerMonitor(StatsMonitor):
    """ Similar to JobMonitor.
    """

    def get_objects(self):
        return Worker.objects.all()

    def new_stats(self, obj, value):
        return self.model_cls(
            worker=obj,
            value=value,
        )
