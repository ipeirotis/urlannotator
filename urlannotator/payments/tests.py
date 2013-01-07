import mock

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson

from urlannotator.payments.models import (BTMBonusPayment,
    PAYMENT_STATUS_INITIALIZED, JobCharge)
from urlannotator.flow_control.test import ToolsMockedMixin
from urlannotator.main.models import (Job, Worker, LABEL_YES,
    worker_type_to_sample_source, JOB_SOURCE_MTURK_WORKFORCE)
from urlannotator.crowdsourcing.models import BeatTheMachineSample

from tagapi.error import TagasaurisApiException


class BTMBonusPaymentTests(ToolsMockedMixin, TestCase):

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
        self.job.btm_points_to_cash = 2
        self.job.save()
        self.job = Job.objects.get(id=self.job.id)

        self.workers = [Worker.objects.create_tagasauris(external_id=x)
            for x in xrange(2)]

    def testEmptyCreation(self):
        BeatTheMachineSample.objects.all().delete()
        self.assertEqual(BeatTheMachineSample.objects.count(), 0)

        worker = Worker.objects.get(external_id=1)

        payment = BTMBonusPayment.objects.create_for_worker(worker, self.job)
        self.assertEqual(payment.points_covered, 0)
        self.assertEqual(payment.amount, 0)
        self.assertEqual(payment.beatthemachinesample_set.count(), 0)
        self.assertEqual(BeatTheMachineSample.objects.count(), 0)

        BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker_type_to_sample_source[worker.worker_type],
            source_val=worker.external_id + '1',
            points=4,
        )

        payment = BTMBonusPayment.objects.create_for_worker(worker, self.job)
        self.assertEqual(payment.points_covered, 0)
        self.assertEqual(payment.amount, 0)
        self.assertEqual(payment.beatthemachinesample_set.count(), 0)

        btm = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker_type_to_sample_source[worker.worker_type],
            source_val=worker.external_id,
            points=2,
        )
        payment = BTMBonusPayment.objects.create_for_worker(worker, self.job)
        self.assertEqual(payment.points_covered, 2)
        self.assertEqual(payment.amount, 1)
        self.assertTrue(btm in payment.beatthemachinesample_set.all())

        btm1 = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker_type_to_sample_source[worker.worker_type],
            source_val=worker.external_id,
            points=2,
        )
        btm2 = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker_type_to_sample_source[worker.worker_type],
            source_val=worker.external_id,
            points=4,
        )
        btm3 = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker_type_to_sample_source[worker.worker_type],
            source_val=worker.external_id,
            points=60,
        )

        payment = BTMBonusPayment.objects.create_for_worker(worker, self.job)
        self.assertEqual(payment.points_covered, 66)
        self.assertEqual(payment.amount, 33)
        self.assertTrue(btm1 in payment.beatthemachinesample_set.all())
        self.assertTrue(btm2 in payment.beatthemachinesample_set.all())
        self.assertTrue(btm3 in payment.beatthemachinesample_set.all())

        self.assertEqual(BeatTheMachineSample.objects.count(), 5)
        self.assertEqual(BeatTheMachineSample.objects.filter(
            frozen=True).count(), 4)
        self.assertEqual(BeatTheMachineSample.objects.filter(
            frozen=False).count(), 1)

    def testTagasaurisPayment(self):
        # Twitter worker on devel.tagasauris.com
        twitter_worker = Worker.objects.create_tagasauris(external_id=83)

        # Mturk worker on devel.tagasauris.com
        mturk_worker = Worker.objects.create_tagasauris(external_id=41)

        payment = BTMBonusPayment.objects.create(
            job=self.job,
            worker=twitter_worker,
            amount=1,
            status=PAYMENT_STATUS_INITIALIZED)
        self.assertEqual(payment.amount, 1)

        # This should fail because only mturk worker supports payments
        with self.assertRaises(TagasaurisApiException):
            payment._pay_tagasauris_bonus()

        payment = BTMBonusPayment.objects.create(
            job=self.job,
            worker=mturk_worker,
            amount=1,
            status=PAYMENT_STATUS_INITIALIZED)
        self.assertEqual(payment.amount, 1)

        payment._pay_tagasauris_bonus()


class StripeTests(ToolsMockedMixin, TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        prefix = 'urlannotator.payments.stripe_handlers.'
        self.mocks = [
            ('{0}stripe.Customer.create'.format(prefix), self._customer_mock),
            ('{0}stripe.Charge.create'.format(prefix), self._charge_mock),
            ('{0}stripe.Event.retrieve'.format(prefix), self._event_mock),
        ]

        self.mocks = [mock.patch(target, new, spec=True, spec_set=True)
            for target, new in self.mocks]

        map(lambda x: x.start(), self.mocks)

    def _customer_mock(self, *args, **kwargs):
        return mock.Mock(id="test_customer")

    def _charge_mock(self, *args, **kwargs):
        return {
            "id": "test_charge",
        }

    def _event_mock(self, *args, **kwargs):
        return mock.Mock(wraps=self.event,
            to_dict=mock.Mock(return_value=self.event))

    def tearDown(self):
        map(lambda x: x.stop(), self.mocks)

    def _test_charge(self, event_name):
        self.client.login(username='testing', password='test')

        gold_urls = ['http://google.com'] + \
            ['http://google.com/' + str(x) for x in xrange(1, 10)]

        post_data = {
            'topic': 'Test Stripe',
            'topic_desc': 'Stripe test job',
            'no_of_urls': '1',
            'data_source': str(JOB_SOURCE_MTURK_WORKFORCE),
            'same_domain': '10',
            'stripeToken': 'abc',
            'gold_urls_positive': '\n'.join(gold_urls[:5]),
            'gold_urls_negative': '\n'.join(gold_urls[5:]),
        }

        r = self.client.post(reverse('project_wizard'), data=post_data,
            follow=True)
        self.assertEqual(r.status_code, 200, "Error when creating job")

        try:
            j = Job.objects.get(account__user=self.u)
        except Exception, e:
            self.fail("Failed to create job - {0}".format(e))

        self.assertFalse(j.is_active(), "Job is active!")
        self.assertTrue(j.is_draft(), "Job is not a draft!")

        try:
            JobCharge.objects.get(job=j)
        except Exception, e:
            self.fail("JobCharge wasn't created! {0}".format(e))

        event_data = {
            "id": "test_event",
            "type": "charge.succeeded",
            "data": {
                "object": {
                    "id": "test_charge",
                },
            },
        }

        # Send `charge.succeeded` event
        self.event = event_data
        r = self.client.post(reverse('payments:stripe_callback'),
            data=simplejson.dumps(event_data), content_type='application/json',
            follow=True)
        j = Job.objects.get(pk=j.pk)
        self.assertEqual(r.status_code, 200,
            "Stripe callback failed: {0}".format(r.content))
        self.assertTrue(j.is_active(), "Job isn't active!")
        self.assertFalse(j.is_draft(),
            "Job shouldn't be a draft after successfull charge")

        self.event.update({'type': event_name})
        r = self.client.post(reverse('payments:stripe_callback'),
            data=simplejson.dumps(event_data), content_type='application/json',
            follow=True)
        j = Job.objects.get(pk=j.pk)
        self.assertEqual(r.status_code, 200,
            "Stripe callback failed: {0}".format(r.content))
        self.assertFalse(j.is_active(), "Job shouldn't be active!")
        self.assertFalse(j.is_draft(),
            "Job shouldn't be a draft after successfull charge")
        self.assertTrue(j.is_stopped(), "Job is not stopped!")

    def test_charge_succeeded_and_failed(self):
        self._test_charge('charge.failed')

    def test_charge_succeeded_and_refund(self):
        self._test_charge('charge.refunded')

    def test_charge_succeeded_and_dispute(self):
        self._test_charge('charge.dispute.created')
