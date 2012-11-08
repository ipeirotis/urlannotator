# Contains job handlers that are responsible for job source-specific actions
# regarding sample gathering, voting and BTM.
# They are gathered in this single place for easier modification later on.
from urlannotator.crowdsourcing.tagasauris_helper import (
    create_btm_voting_with_samples, make_tagapi_client,
    update_voting_with_samples, init_tagasauris_job)
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

    def btm_hit_changed(self, old, new, **kwargs):
        '''
            Fired on 'EventBTMHITChanged'.
        '''


class OwnWorkforceHandler(CrowdsourcingJobHandler):
    '''
        OwnWorkforce job source handler. Uses Tagasauris for all 3 tasks.
    '''
    def init_job(self, **kwargs):
        init_tagasauris_job(self.job)

    def update_btm(self, btm_samples, **kwargs):
        tc = make_tagapi_client()
        samples = (btm.sample for btm in btm_samples)

        tag_jobs = self.job.tagasaurisjobs.voting_btm_key
        # Job has no BTM key - create a new job
        if not tag_jobs.voting_btm_key:
            # Creates sample to mediaobject mapping
            create_btm_voting_with_samples(tc, self.job, samples)
        else:
            update_voting_with_samples(tc, self.job, samples)


handlers = {
    JOB_SOURCE_OWN_WORKFORCE: OwnWorkforceHandler,
}


def get_job_handler(job):
    handler_class = handlers.get(job.data_source, None)
    if not handler_class:
        log.warning('Missing handler for job source %s.' % job.data_source)
        return handler_class

    return handler_class(job=job)
