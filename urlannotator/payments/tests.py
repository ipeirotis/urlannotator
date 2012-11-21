from django.contrib.auth.models import User
from django.test import TestCase

from urlannotator.payments.models import BTMBonusPayment
from urlannotator.flow_control.test import ToolsMockedMixin
from urlannotator.main.models import Job, Worker, LABEL_YES
from urlannotator.crowdsourcing.models import BeatTheMachineSample


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
            source_type=worker.external_id + '1',
            source_val=worker.worker_type,
            points=4,
        )

        payment = BTMBonusPayment.objects.create_for_worker(worker, self.job)
        self.assertEqual(payment.points_covered, 0)
        self.assertEqual(payment.amount, 0)
        self.assertEqual(payment.beatthemachinesample_set.count(), 0)

        btm = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker.external_id,
            source_val=worker.worker_type,
            points=2,
        )

        payment = BTMBonusPayment.objects.create_for_worker(worker, self.job)
        self.assertEqual(payment.points_covered, 2)
        self.assertEqual(payment.amount, 1)
        self.assertTrue(btm in payment.beatthemachinesample_set.all())

        btm1 = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker.external_id,
            source_val=worker.worker_type,
            points=2,
        )
        btm2 = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker.external_id,
            source_val=worker.worker_type,
            points=4,
        )
        btm3 = BeatTheMachineSample.objects.create(
            job=self.job,
            source_type=worker.external_id,
            source_val=worker.worker_type,
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
