import mock
import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from celery import task

from urlannotator.main.models import (Job, Sample, LABEL_YES, LABEL_NO,
    LABEL_BROKEN, Worker)
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_sample_gather, sample_to_mediaobject, stop_job, create_btm,
    samples_to_mediaobjects)
from urlannotator.crowdsourcing.models import (SampleMapping, TagasaurisJobs,
    BeatTheMachineSample)
from urlannotator.flow_control.test import ToolsMockedMixin, ToolsMocked
from urlannotator.flow_control import send_event
from urlannotator.classification.event_handlers import (train,
    SampleGatheringHITMonitor, VotingHITMonitor)
from urlannotator.crowdsourcing.event_handlers import WorkerBTMNotification


def backoff(*args, **kwargs):
    for _ in xrange(30):
        yield 2
    yield 0


class TagasaurisHelperTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])
        self.sample = Sample.objects.all()[0]

        self.mock = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper.BACKOFF_GENERATOR',
            backoff
        )
        self.mock.start()
        self.tc = make_tagapi_client()

    def tearDown(self):
        self.mock.stop()

    def testCreateJob(self):
        voting_key, voting_hit = create_sample_gather(self.tc, self.job)
        self.assertEqual(len(voting_hit), 32)
        self.assertEqual(len(voting_key), 32)

    def testJobDistinctHID(self):
        voting_key_1, voting_hit_1 = create_sample_gather(self.tc, self.job)
        voting_key_2, voting_hit_2 = create_sample_gather(self.tc, self.job)
        self.assertNotEqual(voting_key_1, voting_key_2)
        self.assertNotEqual(voting_hit_1, voting_hit_2)

    def testSampleConvertion(self):
        self.sample.screenshot = 'test_123'
        mo = sample_to_mediaobject(self.sample)
        self.assertEqual(len(mo['id']), 32)
        self.assertEqual(mo['url'], self.sample.screenshot)
        self.assertEqual(mo['mimetype'], 'image/png')

        self.sample.screenshot = None
        self.assertEqual({}, samples_to_mediaobjects([self.sample, ]))

    def testCreateAndStop(self):
        voting_key, voting_hit = create_sample_gather(self.tc, self.job)

        result = self.tc.get_job(external_id=voting_key)
        self.assertNotEqual(result['state'], 'stopped')

        stop_job(voting_key)

        result = self.tc.get_job(external_id=voting_key)
        self.assertEqual(result['state'], 'stopped')

    def testBTMCreation(self):
        btm_key, btm_hit = create_btm(self.tc, self.job, "topic",
            "description", 10)
        self.assertEqual(len(btm_hit), 32)
        self.assertEqual(len(btm_key), 32)


class TagasaurisInApi(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='test', password='test')
        self.user.is_superuser = True
        self.user.save()

        self.c = Client()
        self.mock = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper.BACKOFF_GENERATOR',
            backoff
        )
        self.mock.start()
        self.tc = make_tagapi_client()

        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.user.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

    def tearDown(self):
        self.mock.stop()

    def testCreateAndStop(self):
        # From closing tagasauris job view there is no difference between those
        # jobs - sample gather & voting
        voting_key, voting_hit = create_sample_gather(self.tc, self.job)
        sample_gathering_key, sample_gathering_hit = create_sample_gather(
            self.tc, self.job)

        tj, new = TagasaurisJobs.objects.\
            get_or_create(urlannotator_job=self.job)
        TagasaurisJobs.objects.filter(pk=tj.pk).update(
            sample_gathering_key=sample_gathering_key,
            sample_gathering_hit=sample_gathering_hit,
            voting_key=voting_key,
            voting_hit=voting_hit
        )

        result = self.tc.get_job(external_id=voting_key)
        self.assertNotEqual(result['state'], 'stopped')
        result = self.tc.get_job(external_id=sample_gathering_key)
        self.assertNotEqual(result['state'], 'stopped')

        self.c.login(username='test', password='test')

        resp = self.c.get('%sadmin/job/%d/stop_sample_gathering/?format=json'
            % (self.api_url, self.job.id))

        self.assertEqual(resp.status_code, 200)
        array = json.loads(resp.content)
        self.assertEqual(array['result'], 'SUCCESS')
        result = self.tc.get_job(external_id=sample_gathering_key)
        self.assertEqual(result['state'], 'stopped')
        result = self.tc.get_job(external_id=voting_key)
        self.assertNotEqual(result['state'], 'stopped')

        resp = self.c.get('%sadmin/job/%d/stop_voting/?format=json'
            % (self.api_url, self.job.id))

        self.assertEqual(resp.status_code, 200)
        array = json.loads(resp.content)
        self.assertEqual(array['result'], 'SUCCESS')
        result = self.tc.get_job(external_id=sample_gathering_key)
        self.assertEqual(result['state'], 'stopped')
        result = self.tc.get_job(external_id=voting_key)
        self.assertEqual(result['state'], 'stopped')


class TagasaurisJobCreationChain(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.mock = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper.BACKOFF_GENERATOR',
            backoff
        )
        self.mock.start()

    def tearDown(self):
        self.mock.stop()

    def testSampleGatherOnJobCreation(self):

        @task()
        def mocked_task(*args, **kwargs):
            return True

        def eager_train(kwargs, *args, **kwds):
            train(set_id=kwargs['set_id'])

        mocks = [
            ('urlannotator.main.factories.web_content_extraction', mocked_task),
            ('urlannotator.main.factories.web_screenshot_extraction', mocked_task),
            ('urlannotator.classification.event_handlers.process_execute', eager_train),
        ]

        with ToolsMocked(mocks, add_hardcoded_mocks=False):
            self.job = Job.objects.create_active(
                title='urlannotator_test_tagapi_client',
                description='test_description',
                no_of_urls=2,
                account=self.u.get_profile(),
                gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

        self.assertEqual(TagasaurisJobs.objects.count(), 1)
        tj = TagasaurisJobs.objects.all()[0]
        self.assertEqual(tj.urlannotator_job.id, self.job.id)
        self.assertEqual(len(tj.sample_gathering_key), 32)
        SampleGatheringHITMonitor.delay()
        tj = TagasaurisJobs.objects.all()[0]
        self.assertEqual(len(tj.sample_gathering_hit), 32)


class TagasaurisSampleVotingTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[
                {'url': '10clouds.com/1', 'label': LABEL_YES},
                {'url': '10clouds.com/2', 'label': LABEL_YES},
                {'url': '10clouds.com/3', 'label': LABEL_YES}
            ]
        )

        TagasaurisJobs.objects.get_or_create(urlannotator_job=self.job)

        Sample.objects.all().update(
            screenshot="http://www.10clouds.com/media/v1334047194.07/10c/images/10c_logo.png"
        )
        self.mock = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper.BACKOFF_GENERATOR',
            backoff
        )
        self.mock.start()

    def tearDown(self):
        self.mock.stop()

    def testEventSamplesVoting(self):
        self.assertEqual(TagasaurisJobs.objects.count(), 1)
        self.assertEqual(TagasaurisJobs.objects.all()[0].voting_key, None)
        self.assertEqual(TagasaurisJobs.objects.all()[0].voting_hit, None)

        send_event('EventSamplesVoting')

        self.assertEqual(SampleMapping.objects.count(), 3)

        self.assertEqual(SampleMapping.objects.all()[0].crowscourcing_type,
            SampleMapping.TAGASAURIS)
        self.assertEqual(len(SampleMapping.objects.all()[0].external_id), 32)

        self.assertEqual(TagasaurisJobs.objects.count(), 1)
        self.assertEqual(len(TagasaurisJobs.objects.all()[0].voting_key), 32)
        VotingHITMonitor.delay()
        self.assertEqual(len(TagasaurisJobs.objects.all()[0].voting_hit), 32)


class TagasaurisJobsModelTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

    def testJobUrlsGeneration(self):

        tj, new = TagasaurisJobs.objects.\
            get_or_create(urlannotator_job=self.job)

        self.assertEqual(tj.get_sample_gathering_url(), '')
        self.assertEqual(tj.get_voting_url(), '')

        tj.sample_gathering_hit = '123'
        tj.save()

        self.assertTrue(tj.sample_gathering_hit in
            tj.get_sample_gathering_url())
        self.assertTrue('tagasauris' in tj.get_sample_gathering_url())
        self.assertTrue('annotation' in tj.get_sample_gathering_url())
        self.assertEqual(tj.get_voting_url(), '')

        tj.voting_hit = '456'
        tj.save()

        self.assertTrue(tj.sample_gathering_hit in
            tj.get_sample_gathering_url())
        self.assertTrue('tagasauris' in tj.get_sample_gathering_url())
        self.assertTrue('annotation' in tj.get_sample_gathering_url())
        self.assertTrue(tj.voting_hit in
            tj.get_voting_url())
        self.assertTrue('tagasauris' in tj.get_voting_url())
        self.assertTrue('annotation' in tj.get_voting_url())


class TagasaurisBTMSampleModel(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[
                {'url': '10clouds.com/1', 'label': LABEL_YES},
                {'url': '10clouds.com/2', 'label': LABEL_YES},
                {'url': '10clouds.com/3', 'label': LABEL_YES}
            ]
        )

        TagasaurisJobs.objects.get_or_create(urlannotator_job=self.job)

        self.mocks = []
        m = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper._create_job',
            mock.MagicMock(return_value=('1', '2'))
        )
        self.mocks.append(m)

        m = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper.update_voting_job',
            mock.MagicMock(return_value=True)
        )
        self.mocks.append(m)

        map(lambda x: x.start(), self.mocks)

        self.btm_sample = BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/1',
            label='',
            expected_output=LABEL_YES,
            worker_id=1234
        )
        # Now with sample pinned.
        self.btm_sample = BeatTheMachineSample.objects.get(
            id=self.btm_sample.id)

    def tearDown(self):
        map(lambda x: x.stop(), self.mocks)

    def testSampleCreation(self):
        samples = Sample.objects.count()
        btms = BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/2',
            label='',
            expected_output=LABEL_YES,
            worker_id=1234
        )
        self.assertEqual(samples + 1, Sample.objects.count())
        self.assertTrue('google.com/2' in BeatTheMachineSample.objects.get(
            id=btms.id).sample.url)

    def testConfidenceCalc(self):
        self.assertEqual(self.btm_sample.confidence_level(1.0),
            BeatTheMachineSample.CONF_HIGH)
        self.assertEqual(self.btm_sample.confidence_level(0.75),
            BeatTheMachineSample.CONF_MEDIUM)
        self.assertEqual(self.btm_sample.confidence_level(0.1),
            BeatTheMachineSample.CONF_LOW)

    def testConfidenceGet(self):
        self.btm_sample.label_probability = {
            LABEL_YES: 0.1,
            LABEL_NO: 0.4,
            LABEL_BROKEN: 0.5,
        }

        self.btm_sample.label = LABEL_YES
        self.assertEqual(self.btm_sample.confidence, 0.2)

        self.btm_sample.label = LABEL_NO
        self.assertEqual(self.btm_sample.confidence, 0.8)

        self.btm_sample.label = LABEL_BROKEN
        self.assertEqual(self.btm_sample.confidence, 0.0)

    def testCalculateStatus(self):
        self.btm_sample.label = LABEL_YES
        lab_yes_prob = BeatTheMachineSample.CONF_HIGH_TRESHOLD + 0.01
        self.btm_sample.label_probability = {
            LABEL_YES: lab_yes_prob,
            LABEL_NO: 1.0 - lab_yes_prob,
        }
        self.assertEqual(self.btm_sample.calculate_status(),
            BeatTheMachineSample.BTM_KNOWN)

        self.btm_sample.label = LABEL_YES
        lab_yes_prob = BeatTheMachineSample.CONF_MEDIUM_TRESHOLD + 0.01
        self.btm_sample.label_probability = {
            LABEL_YES: lab_yes_prob,
            LABEL_NO: 1.0 - lab_yes_prob,
        }
        self.assertEqual(self.btm_sample.calculate_status(),
            BeatTheMachineSample.BTM_HUMAN)

        self.btm_sample.label = LABEL_NO
        lab_no_prob = BeatTheMachineSample.CONF_MEDIUM_TRESHOLD + 0.01
        self.btm_sample.label_probability = {
            LABEL_YES: 1.0 - lab_no_prob,
            LABEL_NO: lab_no_prob}
        self.assertEqual(self.btm_sample.calculate_status(),
            BeatTheMachineSample.BTM_HUMAN)

        self.btm_sample.label = LABEL_NO
        lab_no_prob = BeatTheMachineSample.CONF_HIGH_TRESHOLD + 0.01
        self.btm_sample.label_probability = {
            LABEL_YES: 1.0 - lab_no_prob,
            LABEL_NO: lab_no_prob}
        self.assertEqual(self.btm_sample.calculate_status(),
            BeatTheMachineSample.BTM_HUMAN)

    def testUpdateStatus(self):
        self.btm_sample.label = LABEL_NO
        no_prob = BeatTheMachineSample.CONF_HIGH_TRESHOLD + 0.01
        self.btm_sample.label_probability = {
            LABEL_NO: no_prob,
            LABEL_YES: 1.0 - no_prob,
            }
        self.assertEqual(self.btm_sample.calculate_status(),
            BeatTheMachineSample.BTM_HUMAN)

        self.assertNotEqual(self.btm_sample.sample, None)
        self.btm_sample.updateBTMStatus()

        self.assertEqual(TagasaurisJobs.objects.count(), 1)
        # Test below requires tools to be turned off so that Tagasauris is
        # used
        # tj = TagasaurisJobs.objects.all()[0]
        # self.assertEqual(len(tj.voting_btm_key), 32)

    def testHumanRecalculate(self):
        btm = BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/321',
            label='',
            expected_output=LABEL_NO,
            worker_id=1234
        )
        btm = BeatTheMachineSample.objects.get(id=btm.id)

        def recalc(btm_sample, clasifier, human, lab_prob):
            btm_sample.label = clasifier
            btm_sample.label_probability = {
                LABEL_YES: 1.0 - lab_prob,
                LABEL_NO: 1.0 - lab_prob}
            btm_sample.label_probability[clasifier] = lab_prob
            btm_sample.recalculate_human(human)

        #
        # CLASSIFIER SAYS "NO"
        human = LABEL_YES
        recalc(btm, LABEL_NO, human, BeatTheMachineSample.CONF_HIGH_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_KNOWN)
        self.assertTrue(btm.points == 0)

        human = LABEL_YES
        recalc(btm, LABEL_NO, human, BeatTheMachineSample.CONF_MEDIUM_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_X_CORRECTED)
        self.assertEqual(btm.human_label.lower(), human.lower())
        self.assertTrue(btm.points > 0)

        human = LABEL_NO
        recalc(btm, LABEL_NO, human, BeatTheMachineSample.CONF_MEDIUM_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_KNOWN_UNSURE)
        self.assertEqual(btm.human_label.lower(), human.lower())
        self.assertTrue(btm.points > 0)

        #
        # CLASSIFIER SAYS "YES"
        human = LABEL_YES
        recalc(btm, LABEL_YES, human, BeatTheMachineSample.CONF_HIGH_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_NOT_NONX)
        self.assertEqual(btm.human_label.lower(), human.lower())
        self.assertTrue(btm.points == 0)

        human = LABEL_NO
        recalc(btm, LABEL_YES, human, BeatTheMachineSample.CONF_HIGH_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_HOLE)
        self.assertEqual(btm.human_label.lower(), human.lower())
        self.assertTrue(btm.points > 0)

        human = LABEL_YES
        recalc(btm, LABEL_YES, human, BeatTheMachineSample.CONF_MEDIUM_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_KNOWN_UNSURE)
        self.assertEqual(btm.human_label.lower(), human.lower())
        self.assertTrue(btm.points > 0)

        human = LABEL_NO
        recalc(btm, LABEL_YES, human, BeatTheMachineSample.CONF_MEDIUM_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_NOTX_CORRECTED)
        self.assertEqual(btm.human_label.lower(), human.lower())
        self.assertTrue(btm.points > 0)

    def testBTMWorkerNotification(self):
        worker_id = 41  # Mturk worker - notification should work
        Worker.objects.create_tagasauris(external_id=worker_id)

        btm = BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/321',
            label='',
            expected_output=LABEL_YES,
            worker_id=worker_id,
            points_change=True,
        )
        WorkerBTMNotification.delay()

        self.assertFalse(
            BeatTheMachineSample.objects.get(id=btm.id).points_change)

    def testSampleManager(self):

        def make_btm(btm_status):
            BeatTheMachineSample.objects.create_by_worker(
                btm_status=btm_status,
                job=self.job,
                url='google.com/31221',
                worker_id=1234
            )

        make_btm(BeatTheMachineSample.BTM_PENDING)
        make_btm(BeatTheMachineSample.BTM_NO_STATUS)
        make_btm(BeatTheMachineSample.BTM_HUMAN)
        make_btm(BeatTheMachineSample.BTM_KNOWN)
        make_btm(BeatTheMachineSample.BTM_KNOWN_UNSURE)
        make_btm(BeatTheMachineSample.BTM_X_CORRECTED)
        make_btm(BeatTheMachineSample.BTM_NOTX_CORRECTED)
        make_btm(BeatTheMachineSample.BTM_HOLE)
        make_btm(BeatTheMachineSample.BTM_NOT_NONX)

        self.assertTrue(BeatTheMachineSample.objects.count() > 8)

        statuses = [x.btm_status for x in
            BeatTheMachineSample.objects.get_btm_verified(self.job)]

        self.assertTrue(BeatTheMachineSample.BTM_PENDING not in statuses)
        self.assertTrue(BeatTheMachineSample.BTM_NO_STATUS not in statuses)
        self.assertTrue(BeatTheMachineSample.BTM_HUMAN not in statuses)

        self.assertEqual(
            BeatTheMachineSample.objects.get_all_btm(self.job).count(),
            BeatTheMachineSample.objects.filter(job=self.job).count())

        self.assertTrue(
            BeatTheMachineSample.objects.get_all_ready(self.job).count() > 0)


class TagasaurisBTMSideEffects(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[
                {'url': '10clouds.com/1', 'label': LABEL_YES},
                {'url': '10clouds.com/2', 'label': LABEL_YES},
                {'url': '10clouds.com/3', 'label': LABEL_YES}
            ]
        )

        TagasaurisJobs.objects.get_or_create(urlannotator_job=self.job)

        Sample.objects.all().update(
            screenshot="http://www.10clouds.com/media/v1334047194.07/10c/images/10c_logo.png"
        )

        self.mocks = []
        m = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper._create_job',
            mock.MagicMock(return_value=('1', '2'))
        )
        self.mocks.append(m)

        m = mock.patch(
            'urlannotator.crowdsourcing.tagasauris_helper.update_voting_job',
            mock.MagicMock(return_value=True)
        )
        self.mocks.append(m)

        map(lambda x: x.start(), self.mocks)

    def tearDown(self):
        map(lambda x: x.stop(), self.mocks)

    def testBTMSampleIsNoVoting(self):
        self.assertEqual(Sample.objects.filter(btm_sample=False).count(), 3)
        self.assertEqual(Sample.objects.filter(btm_sample=True).count(), 0)

        send_event('EventSamplesVoting')

        # Only 3 gold samples! No BTM Samples!
        self.assertEqual(SampleMapping.objects.count(), 3)

        BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/1',
            label='',
            expected_output=LABEL_YES,
            worker_id=1234
        )
        BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/2',
            label='',
            expected_output=LABEL_YES,
            worker_id=12345
        )

        self.assertEqual(Sample.objects.filter(btm_sample=False).count(), 3)
        self.assertEqual(Sample.objects.filter(btm_sample=True).count(), 2)

        # BTM samples should be considered as BTM_HUMAN - sent to verification
        self.assertEqual(SampleMapping.objects.count(), 5)

        Sample.objects.filter(btm_sample=True).update(vote_sample=True)

        # Sample must have screenshot
        Sample.objects.all().update(
            screenshot="http://www.10clouds.com/media/v1334047194.07/10c/images/10c_logo.png"
        )

        send_event('EventSamplesVoting')

        # 5 - incude added BTM Samples.
        self.assertEqual(SampleMapping.objects.count(), 5)

    def testBTMSampleFrozen(self):
        btm = BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/321',
            label='',
            expected_output=LABEL_YES,
            worker_id=1234,
        )
        btm.frozen = True
        btm.save()
        btm = BeatTheMachineSample.objects.get(id=btm.id)

        def recalc(btm_sample, clasifier, human, lab_prob):
            btm_sample.label = clasifier
            btm_sample.label_probability = {
                LABEL_YES: 1.0 - lab_prob,
                LABEL_NO: 1.0 - lab_prob}
            btm_sample.label_probability[clasifier] = lab_prob
            btm_sample.recalculate_human(human)

        human = LABEL_YES
        recalc(btm, LABEL_NO, human, BeatTheMachineSample.CONF_MEDIUM_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_PENDING)
        self.assertTrue(btm.points == 0)

        human = LABEL_NO
        recalc(btm, LABEL_YES, human, BeatTheMachineSample.CONF_HIGH_TRESHOLD + 0.01)
        btm = BeatTheMachineSample.objects.get(id=btm.id)
        self.assertEqual(btm.btm_status, BeatTheMachineSample.BTM_PENDING)
        self.assertTrue(btm.points == 0)

    def testUpdatePoints(self):
        btm = BeatTheMachineSample.objects.create_by_worker(
            job=self.job,
            url='google.com/321',
            label='',
            expected_output=LABEL_YES,
            worker_id=1234,
        )

        self.assertEqual(btm.points, 0)
        self.assertEqual(btm.points_change, False)

        btm.update_points(BeatTheMachineSample.BTM_HOLE)
        self.assertNotEqual(btm.points, 0)
        self.assertEqual(btm.points_change, True)
