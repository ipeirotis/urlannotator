# Contains job handlers that are responsible for job source-specific actions
# regarding sample gathering, voting and BTM.
# They are gathered in this single place for easier modification later on.
from urlannotator.crowdsourcing.tagasauris_helper import (
    create_btm_voting_job, make_tagapi_client, init_tagasauris_job,
    create_voting_job, update_voting_job, create_btm, update_voting)
from urlannotator.crowdsourcing.odesk_helper import notify_workers
from urlannotator.crowdsourcing.models import OdeskMetaJob
from urlannotator.main.models import (JOB_SOURCE_ODESK_FREE,
    JOB_SOURCE_OWN_WORKFORCE, JOB_SOURCE_ODESK_PAID)

import logging
log = logging.getLogger(__name__)


class CrowdsourcingJobHandler(object):
    def __init__(self, job):
        self.job = job

    def init_job(self, **kwargs):
        '''
            Initializes job-specific actions when job's initialization is done
            on our side.
            Returns True on success.
        '''
        res = self.init_sample_gathering(**kwargs)
        return res and self.init_voting(**kwargs)

    def init_sample_gathering(self, **kwargs):
        '''
            Initializes the sample gathering job for given job.
            Returns True on success.
        '''
        return False

    def init_voting(self, **kwargs):
        '''
            Initializes the voting job for given job.
            Returns True on success.
        '''
        return False

    def init_btm(self, **kwargs):
        '''
            Initializes the BTM job for given job.
            Returns True on success.
        '''
        return False

    def init_btm_gather(self, **kwargs):
        '''
            Initializes BTM gathering job.
            Returns True on success.
        '''
        return False

    def init_btm_voting(self, **kwargs):
        '''
            Initializes BTM voting job.
            Returns True on success.
        '''
        return False

    def update_sample_gathering(self, **kwargs):
        '''
            Updates sample gathering job tied to given job.
            Returns True on success.
        '''
        return False

    def update_voting(self, samples, **kwargs):
        '''
            Updates voting job tied to given job.
            Returns True on success.
        '''
        return False

    def update_btm(self, btm_samples, **kwargs):
        '''
            Updates BTM job tied to given job.
            Returns True on success.
        '''
        return False

    def sample_gathering_hit_changed(self, old, new, **kwargs):
        '''
            Fired on 'EventSampleGatheringHITChanged'.
        '''

    def voting_hit_changed(self, old, new, **kwargs):
        '''
            Fired on 'EventVotingHITChanged'.
        '''

    def btm_gathering_hit_changed(self, old, new, **kwargs):
        '''
            Fired on 'EventBTMGatheringHITChanged'.
        '''

    def btm_voting_hit_changed(self, old, new, **kwargs):
        '''
            Fired on 'EventBTMVotingHITChanged'.
        '''


class TagasaurisHandler(CrowdsourcingJobHandler):
    '''
        Tagasauris job source handler. Uses Tagasauris for all 3 tasks.
    '''
    def init_job(self, *args, **kwargs):
        try:
            tagjob = self.job.tagasaurisjobs
        except:
            tagjob = None

        if tagjob and tagjob.sample_gathering_hit is not None:
            log.info(
                'Tried to create new sample gathering job, but it already exists'
            )
            return True
        res = init_tagasauris_job(self.job)
        return res

    def init_voting(self, tc, samples, *args, **kwargs):
        if self.job.tagasaurisjobs.voting_hit is not None:
            log.info(
                'Tried to create new voting job, but it already exists'
            )
            return True
        log.info(
            'TagasaurisHandler: Creating voting job for job %d' % self.job.id
        )
        res = create_voting_job(tc, self.job, samples)
        if res:
            log.info(
                'TagasaurisHandler: Created voting job for job %d' % self.job.id
            )
        return res

    def update_voting(self, tc, samples, *args, **kwargs):
        log.info(
            'TagasaurisHandler: Updating voting job for job %d' % self.job.id
        )
        res = update_voting(tc, self.job, samples)
        if res:
            log.info(
                'TagasaurisHandler: Updating voting job for job %d' % self.job.id
            )
        return res

    def init_btm_gather(self, topic, description, no_of_urls, *args, **kwargs):
        if self.job.tagasaurisjobs.beatthemachine_hit is not None:
            log.info(
                'Tried to create new btm gathering job, but it already exists'
            )
            return True
        tc = make_tagapi_client()
        res = create_btm(tc, self.job, topic, description, no_of_urls)
        return res

    def init_btm_voting(self, samples, *args, **kwargs):
        if self.job.tagasaurisjobs.voting_btm_hit is not None:
            log.info(
                'Tried to create new btm voting job, but it already exists'
            )
            return True
        tc = make_tagapi_client()
        create_btm_voting_job(tc, self.job, samples)

    def update_btm(self, btm_samples, *args, **kwargs):
        tc = make_tagapi_client()
        samples = (btm.sample for btm in btm_samples)

        tag_jobs = self.job.tagasaurisjobs
        # Job has no BTM key - create a new job
        if not tag_jobs.voting_btm_key:
            # Creates sample to mediaobject mapping
            self.init_btm_voting(samples)
        else:
            update_voting_job(tc, self.job, samples)


class OdeskHandler(TagasaurisHandler):
    def __init__(self, *args, **kwargs):
        super(OdeskHandler, self).__init__(*args, **kwargs)

    def _init_job(self, t_job, odesk_job, *args, **kwargs):
        func = getattr(super(OdeskHandler, self), t_job)
        res = func(*args, **kwargs)
        if not res:
            return False

        kwargs.pop('job', None)
        res = odesk_job(job=self.job, *args, **kwargs)
        return res is not None

    def init_job(self, *args, **kwargs):
        from urlannotator.crowdsourcing.odesk_helper import (
            create_sample_gather as ctor)
        return self._init_job('init_job', ctor, *args, **kwargs)

    def init_voting(self, *args, **kwargs):
        from urlannotator.crowdsourcing.odesk_helper import (
            create_voting as ctor)
        return self._init_job('init_voting', ctor, *args, **kwargs)

    def init_btm_gather(self, *args, **kwargs):
        from urlannotator.crowdsourcing.odesk_helper import (
            create_btm_gather as ctor)
        return self._init_job('init_btm_gather', ctor, *args, **kwargs)

    def init_btm_voting(self, *args, **kwargs):
        from urlannotator.crowdsourcing.odesk_helper import (
            create_btm_voting as ctor)
        return self._init_job('init_btm_voting', ctor, *args, **kwargs)

    def sample_gathering_hit_changed(self, old, new, **kwargs):
        super(OdeskHandler, self).sample_gathering_hit_changed(
            old=old, new=new, **kwargs)
        try:
            meta = self.job.account.odeskmetajob_set.get(
                job_type=OdeskMetaJob.ODESK_META_SAMPLE_GATHER)
        except OdeskMetaJob.DoesNotExist:
            return
        self.job.account.odeskmetajob_set.filter(pk=meta.pk).update(active=True)
        notify_workers(odesk_job=meta, hit=new, job=self.job)

    def voting_hit_changed(self, old, new, **kwargs):
        super(OdeskHandler, self).voting_hit_changed(
            old=old, new=new, **kwargs)
        try:
            meta = self.job.account.odeskmetajob_set.get(
                job_type=OdeskMetaJob.ODESK_META_VOTING)
        except OdeskMetaJob.DoesNotExist:
            return
        self.job.account.odeskmetajob_set.filter(pk=meta.pk).update(active=True)
        notify_workers(odesk_job=meta, hit=new, job=self.job)

    def btm_gathering_hit_changed(self, old, new, **kwargs):
        super(OdeskHandler, self).btm_gathering_hit_changed(
            old=old, new=new, **kwargs)
        try:
            meta = self.job.account.odeskmetajob_set.get(
                job_type=OdeskMetaJob.ODESK_META_BTM_GATHER)
        except OdeskMetaJob.DoesNotExist:
            return
        self.job.account.odeskmetajob_set.filter(pk=meta.pk).update(active=True)
        notify_workers(odesk_job=meta, hit=new, job=self.job)

    def btm_voting_hit_changed(self, old, new, **kwargs):
        super(OdeskHandler, self).btm_voting_hit_changed(
            old=old, new=new, **kwargs)
        try:
            meta = self.job.account.odeskmetajob_set.get(
                job_type=OdeskMetaJob.ODESK_META_BTM_VOTING)
        except OdeskMetaJob.DoesNotExist:
            return
        self.job.account.odeskmetajob_set.filter(pk=meta.pk).update(active=True)
        notify_workers(odesk_job=meta, hit=new, job=self.job)

handlers = {
    JOB_SOURCE_OWN_WORKFORCE: TagasaurisHandler,
    JOB_SOURCE_ODESK_PAID: OdeskHandler,
    JOB_SOURCE_ODESK_FREE: OdeskHandler
}


def get_job_handler(job):
    handler_class = handlers.get(job.data_source, None)
    if not handler_class:
        log.warning('Missing handler for job source %s.' % job.data_source)
        return TagasaurisHandler(job=job)

    return handler_class(job=job)
