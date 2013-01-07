from django.db import models

from urlannotator.crowdsourcing.tagasauris_helper import make_tagapi_client
from urlannotator.main.models import Job, Worker
from tenclouds.django.jsonfield.fields import JSONField

import logging
log = logging.getLogger(__name__)

# Payment statuses breakdown:
# NOTE: Not every backend could use all of those statuses.
PAYMENT_STATUS_INITIALIZED = 0  # Payment has been initialized by us, but not sent.
                                # It'll be used by the payments monitor to complete
                                # it after certain time since initialization.
PAYMENT_STATUS_ISSUED = 1  # Payment has been issued by us using given backend.
                           # A payment is issued if a request has been sent by us
                           # to the specific service that will complete it.
PAYMENT_STATUS_PENDING = 2  # Payment has been issued and we are awaiting completion.
PAYMENT_STATUS_FINALIZATION = 3  # Payment is being finalized.
PAYMENT_STATUS_COMPLETED = 3  # Payment has been completed successfully.
PAYMENT_STATUS_INITIALIZATION = 4  # Payment is being initialized.

# Error statuses - sub_status field is filled with additional data if possible.
PAYMENT_STATUS_INITIALIZATION_ERROR = 4  # There was an error while initializing the payment.
PAYMENT_STATUS_ISSUED_ERROR = 5  # There was an error while issuing the payment.
PAYMENT_STATUS_FINALIZATION_ERROR = 6  # There was an error during payment finalization.

PAYMENT_STATUS_CHOICES = (
    (PAYMENT_STATUS_INITIALIZED, PAYMENT_STATUS_INITIALIZED),
    (PAYMENT_STATUS_ISSUED, PAYMENT_STATUS_ISSUED),
    (PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PENDING),
    (PAYMENT_STATUS_FINALIZATION, PAYMENT_STATUS_FINALIZATION),
    (PAYMENT_STATUS_COMPLETED, PAYMENT_STATUS_COMPLETED),
    (PAYMENT_STATUS_INITIALIZATION_ERROR, PAYMENT_STATUS_INITIALIZATION_ERROR),
    (PAYMENT_STATUS_ISSUED_ERROR, PAYMENT_STATUS_ISSUED_ERROR),
    (PAYMENT_STATUS_FINALIZATION_ERROR, PAYMENT_STATUS_FINALIZATION_ERROR),
)

# Job tasks breakdown:
JOB_TASK_SAMPLE_GATHERING = 0
JOB_TASK_VOTING = 1
JOB_TASK_BTM = 2

SAMPLE_GATHERING_TASK_NAME = 'gathering'
VOTING_TASK_NAME = 'voting'
BTM_TASK_NAME = 'btm'


task_to_name = {
    JOB_TASK_SAMPLE_GATHERING: SAMPLE_GATHERING_TASK_NAME,
    JOB_TASK_VOTING: VOTING_TASK_NAME,
    JOB_TASK_BTM: BTM_TASK_NAME,
}


JOB_TASK_CHOICES = (
    (JOB_TASK_SAMPLE_GATHERING, JOB_TASK_SAMPLE_GATHERING),
    (JOB_TASK_VOTING, JOB_TASK_VOTING),
    (JOB_TASK_BTM, JOB_TASK_BTM),
)


class WorkerPaymentManager(models.Manager):
    def pay_task(self, worker, job, amount, backend, task):
        return self.create(
            worker=worker,
            job=job,
            amount=amount,
            backend=backend,
            job_task=task,
            status=PAYMENT_STATUS_INITIALIZATION,
        )

    def pay_sample_gathering(self, worker, job, amount, backend):
        return self.pay_task(
            worker=worker,
            job=job,
            amount=amount,
            backend=backend,
            task=JOB_TASK_SAMPLE_GATHERING,
        )

    def pay_voting(self, worker, job, amount, backend):
        return self.pay_task(
            worker=worker,
            job=job,
            amount=amount,
            backend=backend,
            task=JOB_TASK_VOTING,
        )

    def pay_btm(self, worker, job, amount, backend):
        return self.pay_task(
            worker=worker,
            job=job,
            amount=amount,
            backend=backend,
            task=JOB_TASK_BTM,
        )

    def get_sample_gathering(self, job):
        return self.filter(
            job=job,
            job_task=JOB_TASK_SAMPLE_GATHERING,
        )

    def get_voting(self, job):
        return self.filter(
            job=job,
            job_task=JOB_TASK_VOTING,
        )

    def get_btm(self, job):
        return self.filter(
            job=job,
            job_task=JOB_TASK_BTM,
        )

    def _filter_completed(self, payments):
        return payments.filter(status=PAYMENT_STATUS_COMPLETED)

    def _get_total(self, payments):
        return self._filter_completed(
            payments
        ).aggregate(models.Sum('amount'))['amount__sum']

    def get_sample_gathering_total(self, job):
        return self._get_total(
            self.get_sample_gathering(
                job=job,
            )
        )

    def get_voting_total(self, job):
        return self._get_total(
            self.get_voting(
                job=job,
            )
        )

    def get_btm_total(self, job):
        return self._get_total(
            self.get_btm(
                job=job,
            )
        )


class JobPaymentSettings(models.Model):
    job = models.ForeignKey(Job)
    split_budget = JSONField(default='{}')
    backend = models.CharField(max_length=50)
    main = models.BooleanField(default=True)
    backend_params = JSONField(default='{}')

    class Meta:
        unique_together = ['job', 'main']


class WorkerPayment(models.Model):
    job = models.ForeignKey(Job)
    worker = models.ForeignKey(Worker)
    amount = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    backend = models.CharField(max_length=50)
    status = models.PositiveIntegerField(choices=PAYMENT_STATUS_CHOICES)
    sub_status = models.CharField(max_length=50)
    job_task = models.PositiveIntegerField(choices=JOB_TASK_CHOICES)
    combined_payment = models.ForeignKey('WorkerPayment', null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    additional_data = JSONField(default='{}')

    objects = WorkerPaymentManager()

    def is_completed(self):
        return self.status == PAYMENT_STATUS_COMPLETED

    def set_status(self, status):
        self.status = status
        WorkerPayment.objects.filter(id=self.id).update(status=status)

    def complete(self):
        self.set_status(PAYMENT_STATUS_COMPLETED)

    def is_issued(self):
        return self.status == PAYMENT_STATUS_ISSUED

    def is_pending(self):
        return self.status == PAYMENT_STATUS_PENDING

    def is_finalizing(self):
        return self.status == PAYMENT_STATUS_FINALIZATION

    def is_initialized(self):
        return self.status == PAYMENT_STATUS_INITIALIZED

    def is_combined_payment(self):
        return self.combined_payment_id is not None


class BTMBonusPaymentManager(models.Manager):

    def create_for_worker(self, worker, job, *args, **kwargs):
        kwargs['job'] = job
        kwargs['worker'] = worker
        kwargs['status'] = PAYMENT_STATUS_INITIALIZED
        payment = self.create(*args, **kwargs)

        from urlannotator.crowdsourcing.models import BeatTheMachineSample
        samples = BeatTheMachineSample.objects.from_worker_unpaid(
            worker).filter(job=payment.job)
        samples.update(
            frozen=True,
            payment=payment
        )

        for sample in payment.beatthemachinesample_set.all():
            points = sample.points
            payment.points_covered += points

            amount = float(points) / sample.job.btm_points_to_cash
            payment.amount += amount
        payment.save()
        return payment


class BTMBonusPayment(models.Model):
    """
        Bonus payment for worker BTM Samples. Gathered BTMSamples should be
        frozen before bonus payment creation. This payment can cover single job.
    """
    job = models.ForeignKey(Job, null=True)
    worker = models.ForeignKey(Worker)
    points_covered = models.IntegerField(default=0)
    amount = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    status = models.PositiveIntegerField(choices=PAYMENT_STATUS_CHOICES)
    sub_status = models.CharField(max_length=50, blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    additional_data = JSONField(default='{}')

    objects = BTMBonusPaymentManager()

    def _pay_tagasauris_bonus(self):
        tc = make_tagapi_client()
        tc.pay_worker_bonus(
            worker_id=int(self.worker.external_id),
            amount=self.amount,
            reason='Bonus for Beat The Machine job no %s' % self.job.id)

    def _pay_odesk_bonus(self):
        """
        Not tested yet.
        """
        from urlannotator.crowdsourcing.models import OdeskJob, OdeskMetaJob
        from urlannotator.crowdsourcing.odesk_helper import (
            make_client_from_job, JOB_BTM_GATHERING_KEY)

        oc = make_client_from_job(self.job)

        oj = OdeskJob.objects.filter(
            meta_job__acount=self.job.account,
            meta_job__job_type=OdeskMetaJob.ODESK_META_BTM_GATHER)

        oc.hr.post_team_adjustment(
            team_reference=self.job.account.odesk_teams[
                JOB_BTM_GATHERING_KEY],
            engagement_reference=oj.engagement_id,
            amount=self.amount,
            comments='Bonus for Beat The Machine job no %s' % self.job.id,
            notes='')

    def pay_bonus(self):
        self._pay_tagasauris_bonus()


class JobChargeException(Exception):
    pass


class JobChargeManager(models.Manager):

    def _from_token(self, stripe_token, description, charge_type):
        from urlannotator.payments.stripe_handlers import stripe_client
        try:
            stripe = stripe_client()
            customer = stripe.Customer.create(
                description=description,
                card=stripe_token
            )
            return self.create(
                customer_id=customer.id,
                charge_type=charge_type,
            )

        except stripe.CardError, e:
            body = e.json_body
            err = body['error']['message']
            raise JobChargeException(err)

        except stripe.InvalidRequestError:
            raise JobChargeException("Stripe: Invalid credit card data")

        # except stripe.AuthenticationError, e:
        # except stripe.APIConnectionError, e:
        except stripe.StripeError, e:
            log.exception(e)
            raise JobChargeException("Stripe temporarily unavailable")

    def base_from_token(self, stripe_token,
            description="BuildAClassifer Customer"):
        return self._from_token(stripe_token, description, JobCharge.Type.BASE_JOB)

    def btm_from_token(self, stripe_token,
            description="BuildAClassifer Customer"):
        return self._from_token(stripe_token, description, JobCharge.Type.BTM_JOB)


class JobCharge(models.Model):
    class Type:
        # The regular job charge
        BASE_JOB = 'base_job'

        # The Beat The Machine job charge
        BTM_JOB = 'btm_job'

    class Currency:
        USD = 'usd'

    TYPE_CHOICES = (
        (Type.BASE_JOB, 'Base job'),
        (Type.BTM_JOB, 'Beat The Machine job'),
    )

    CURRENCY_CHOICES = (
        (Currency.USD, 'USD'),
    )

    job = models.ForeignKey(Job, null=True)
    customer_id = models.CharField(max_length=50)
    charge_id = models.CharField(max_length=50)
    charge_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=50, choices=CURRENCY_CHOICES)

    objects = JobChargeManager()

    def charge(self, amount, description=None):
        """
            Charges linked customer with `amount` in USD dollars.
        """
        from urlannotator.payments.stripe_handlers import stripe_client

        amount_cents = int(amount * 100)
        currency = self.Currency.USD
        stripe = stripe_client()
        desc = description if description else self.get_charge_type_display()

        data = stripe.Charge.create(
            amount=amount_cents,
            currency=currency,
            customer=self.customer_id,
            description=desc,
        )
        self.amount = amount_cents
        self.currency = currency
        self.charge_id = data['id']
        self.save()
