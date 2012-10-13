import uuid
import hashlib

from itertools import ifilter
from troia_client import TroiaClient
from django.conf import settings

from urlannotator.crowdsourcing.models import TroiaJob
from urlannotator.main.models import LABEL_YES, LABEL_NO, LABEL_BROKEN

cost_matrix = [
    (LABEL_YES, {
        LABEL_YES: 0.,
        LABEL_BROKEN: 1.,
        LABEL_NO: 1.,
    }),
    (LABEL_NO, {
        LABEL_NO: 0.,
        LABEL_YES: 1.,
        LABEL_BROKEN: 1.,
    }),
    (LABEL_BROKEN, {
        LABEL_BROKEN: 0.,
        LABEL_NO: 1.,
        LABEL_YES: 1.,
    })
]


def init_troia(job):
    gold_samples = map(
        lambda x: (x.url, x.goldsample.label),
        ifilter(
            lambda x: x.is_gold_sample(),
            job.sample_set.all().iterator()
        )
    )
    make_troia_job(job=job, gold_samples=gold_samples)


def make_troia_job(job, gold_samples=[]):
    """
        Creates Troia job corresponding to passed Job object.
    """
    client = TroiaClient(settings.TROIA_HOST, None)
    job_id = make_job_id(job=job)
    TroiaJob.objects.create(job=job, troia_id=job_id)
    client.reset(job_id)
    client.load_categories(cost_matrix, job_id)
    client.load_gold_labels(gold_samples, job_id)


def make_job_id(job):
    """
        Creates Troia job ID corresponding to passed Job object.
    """
    m = hashlib.sha256('%s%d' % (uuid.uuid4, job.id)).hexdigest()
    return m
