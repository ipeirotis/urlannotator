from urlannotator.payments.models import (PAYMENT_STATUS_COMPLETED,
    WorkerPayment, JobPaymentSettings, task_to_name, JOB_TASK_BTM,
    JOB_TASK_VOTING, JOB_TASK_SAMPLE_GATHERING)


class PaymentBackend(object):

    def __init__(self, job, **kwargs):
        self.job = job

    def issue_payment(self, payment, ensure_funds=True):
        """
            Issues a payment to be completed. Does the actual logic that
            sends the payment to the worker using whatever
            specific API/Platform.

            Ensure that this method is thread-safe and process-safe. If not,
            then we might end up with at least 2 requests made for a single
            payment!
            Returns True on success.
        """
        raise NotImplementedError()

    def ensure_funds(self, amount, bucket):
        """
            Ensures that given :param amount: of money will be available inside.

            Returns True on success.

            :param bucket:
        """
        budget = self.get_split_budget()
        funds = budget[bucket]

        if funds < amount:
            return False

        budget[bucket] = funds - amount
        JobPaymentSettings.objects.filter(
            job=self.job,
            backend=self.backend_name,
        ).update(split_budget=budget)
        return True

    def init_job(self, job, main=True):
        """
            Initializes payment backend for given job.
        """
        JobPaymentSettings.objects.create(
            job=job,
            split_budget=self.get_split_budget(job.budget),
            backend=self.backend_name,
            main=main,
        )
        self.charge_owner(job)

    def charge_owner(self, job):
        """
            Charges :param job: owner's account for job's budget, so we have
            funds to use.
        """
        raise NotImplementedError()

    def join_budgets(self, budget1, budget2):
        """
            Joins to budget splits due to more than one owner's charging.

            :param budget1: - base budget that merge will be done to
            :param budget2: - budget that will be merged.
        """
        for name, val in budget1.iteritems():
            val += budget2.get(name, 0)
            budget1[name] = val

    def can_issue_payment(self, payment):
        """
            Returns whether given payment can be issued now.
        """
        raise NotImplementedError()

    def test_payment(self, job, worker, job_task, amount):
        """
            Checks if a `worker` can be paid for completing `job_task`
            in `job`.
            You have to check it before initializing a payment to avoid issues.
        """
        raise NotImplementedError()

    def initialize_payment(self, job, worker, job_task, amount):
        """
            Initializes payment for `worker` for completing `job_task`
            in `job`.
            Returns whether the payment has been issued.
        """
        payment = WorkerPayment.objects.pay_task(
            job=job,
            worker=worker,
            job_task=job_task,
            amount=amount,
            backend=self.backend_name,
        )
        can_issue = self.can_issue_payment(payment)
        if can_issue:
            self.issue_payment(payment)

        return can_issue

    def get_split_budget(self):
        """
            Returns budget split into each task's budget.
        """
        settings = self.job.jobpaymentsettings_set.get(backend=self.backend_name)
        return settings.split_budget

    def split_budget(self, budget):
        """
            Splits `budget` into budgets of every tasks it consists of.
            DOESN'T submit to DB.
        """
        raise NotImplementedError()

    def get_payment_status(self, payment):
        """
            Returns `payment` status.
        """
        raise NotImplementedError()

    def update_payment_status(self, payment):
        """
            Updates DB status of uncompleted `payment`.
        """
        status = self.get_payment_status()
        WorkerPayment.objects.filter(id=payment).update(status=status)

    def update_payment(self, payment):
        """
            Updates payment's status. If possible, issues, completes or
            finalizes it.
        """
        self.update_payment_status(payment)

    def update_payments(self, payments):
        """
            Updates a list of payments.
        """
        map(lambda x: self.update_payment(x), self.get_running_payments())


class DummyBackend(PaymentBackend):
    """
        Dummy payment backend class used for easy testing.
    """
    backend_name = 'DummyBackend'

    def issue_payment(self, payment, ensure_funds=True):
        """
            Dummy payments are always issued and completed.
        """
        WorkerPayment.objects.filter(id=payment.id).update(status=PAYMENT_STATUS_COMPLETED)
        return True

    def can_issue_payment(self, payment):
        return True

    def test_payment(self, job, worker, job_task, amount):
        split_budget = self.get_split_budget()
        key_name = self.get_free_budget_name(job_task)
        return split_budget.get(key_name, 0) >= amount

    def get_free_budget_name(self, task):
        return '%s-free' % task_to_name(task)

    def split_budget(self, budget):
        """
            Splits budget evenly on sample gathering, voting and btm.
        """
        third = budget / 3.0
        sample_gathering = third
        voting = third
        btm = budget - sample_gathering - voting
        budget = {
            task_to_name(JOB_TASK_SAMPLE_GATHERING): sample_gathering,
            self.get_free_budget_name(JOB_TASK_SAMPLE_GATHERING): sample_gathering,
            task_to_name(JOB_TASK_VOTING): voting,
            self.get_free_budget_name(JOB_TASK_VOTING): voting,
            task_to_name(JOB_TASK_BTM): btm,
            self.get_free_budget_name(JOB_TASK_BTM): btm,
        }
        return budget

    def get_payment_status(self, payment):
        return payment.status


class CombinedPaymentBackend(PaymentBackend):
    """
        Enabled using multiple backends for different job tasks.
        Requires one of them to be set as the `main` backend that does the
        job budget split.
    """
    pass

BUFFER_KEY_NAME = 'buffer'
BUFFER_FREE_KEY_NAME = 'buffer-free'

BUFFER_PERC = 0.1


class BufferPaymentBackend(PaymentBackend):
    """
        Creates a small buffer from job's budget in addition to normal split.
        It's used to cover additional costs, difficult to expect costs.

        Abstract backend.
    """
    backend_name = 'BufferPaymentBackend'

    def __init__(self, buffer_perc, job, **kwargs):
        self.buffer_perc = buffer_perc
        super(BufferPaymentBackend, self).__init__(job=job, **kwargs)

    def init_job(self, job):
        super(BufferPaymentBackend, self).init_job(job=job)
        params = JobPaymentSettings.objects.get(
            job=job,
            backend=self.backend_name,
        ).backend_params
        params['buffer_perc'] = BUFFER_PERC

        JobPaymentSettings.objects.filter(
            job=job,
            backend=self.backend_name,
        ).update(backend_params=params)

    def ensure_funds(self, amount, bucket):
        res = super(BufferPaymentBackend, self).ensure_funds(
            amount=amount,
            bucket=bucket,
        )

        if res:
            return True

        # Regular bucket didn't suffice - we need to use the buffer.
        name = task_to_name(bucket)
        budget = self.get_split_budget()
        budget_val = budget[name]

        if (budget_val >= amount):
            budget[name] = budget_val - amount
            self.job.jobpaymentsettings_set.filter(main=True).update(
                split_budget=budget,
            )
            return True
        else:
            # We don't have enough funds in the appropriate bucket - we have
            # to take money from the buffer.
            amount = amount - budget_val
            buffer_free = budget[BUFFER_FREE_KEY_NAME]

            if buffer_free >= amount:
                # Transfer buffered funds to payment task's bucket.
                budget[name] = amount
                budget[BUFFER_FREE_KEY_NAME] = buffer_free - amount
                self.job.jobpaymentsettings_set.filter(main=True).update(
                    split_budget=budget,
                )
                return True
            return False

    def transfer_to_bucket(self, amount, bucket):
        """
            Transfers given amount of money from the buffer to given bucket.

            Return True on success.
        """
        budget = self.get_split_budget()
        buffer_free = budget[BUFFER_FREE_KEY_NAME]

        if (buffer_free >= amount):
            budget[BUFFER_FREE_KEY_NAME] = buffer_free - amount
            budget[bucket] = budget[bucket] + amount
            self.job.jobpaymentsettings_set.filter(main=True).update(
                split_budget=budget,
            )
            return True
        return False

    def issue_payment(self, payment, ensure_funds=True):
        """
            Checks available funds in the appropriate bucket and buffer.
            If there are any available funds - they are removed from the pool
            of free resources.

            Return True on success.
        """
        # Race condition here from direct payment issue and delayed payments
        # monitor.
        if not payment.is_initialized():
            return False

        bucket_name = task_to_name(payment.job_task) + '-free'
        return self.ensure_funds(amount=payment.amount, bucket=bucket_name)

    def test_payment(self, job, worker, job_task, amount):
        name = task_to_name(job_task) + '-free'
        budget = self.get_split_budget()
        budget_val = budget[name]

        if (budget_val >= amount):
            return True
        else:
            # We don't have enough funds in the appropriate bucket - we have
            # to take money from the buffer.
            amount = amount - budget_val
            buffer_free = budget[BUFFER_FREE_KEY_NAME]

            return buffer_free >= amount

    def split_budget(self, budget):
        buff = round(budget * self.buffer_perc, 2)
        budget = budget - buff
        budget = super(BufferPaymentBackend, self).split_budget(budget)
        budget[BUFFER_KEY_NAME] = buff
        budget[BUFFER_FREE_KEY_NAME] = buff
        return budget


# Minimal, guaranteed salary for a worker regardless of currency.
MINIMAL_DEFAULT_AMOUNT = 1
MINIMAL_DEFAULT_KEY = 'minimal_amount'
RESERVED_FUNDS_KEY = 'reserved'


class MinimalPaymentBackend(BufferPaymentBackend):
    """
        Can be used in cases where each worker has to be paid a minimal,
        guaranteed amount of money.

        Abstract backend.
    """
    def __init__(self, minimal_amount, **kwargs):
        self.minimal_amount = minimal_amount
        super(MinimalPaymentBackend, self).__init__(**kwargs)

    def init_job(self, job):
        super(MinimalPaymentBackend, self).init_job(job=job)
        params = JobPaymentSettings.objects.get(
            job=job,
            backend=self.backend_name,
        ).backend_params
        params[MINIMAL_DEFAULT_KEY] = self.minimal_amount
        JobPaymentSettings.objects.filter(
            job=job,
            backend=self.backend_name,
        ).update(backend_params=params)

    def issue_payment(self, payment, ensure_funds=True):
        """
            Checks available funds in the appropriate bucket.
            If there are any available funds - they are removed from the pool
            of free resources.

            Return True on success.
        """
        # Race condition here from direct payment issue and delayed payments
        # monitor.
        if not payment.is_initialized():
            return False

        amount = payment.amount
        payments = self.job.workerpayment_set.filter(worker=payment.worker)
        if not payments.len():
            # New worker
            res = super(MinimalPaymentBackend, self).issue_payment(
                payment=payment,
            )
            if not res:
                return res
            bucket_name = task_to_name(payment.job_task) + '-free'
        return self.ensure_funds(amount=payment.amount, bucket=bucket_name)

    def split_budget(self, budget):
        budget = super(MinimalPaymentBackend, self).split_budget(budget=budget)
        budget[RESERVED_FUNDS_KEY] = 0
        return budget


class TagasaurisPaymentBackend(PaymentBackend):
    """
        Realizes payments for jobs made by Tagasauris.
    """
    # TODO: Proper Tagasauris API calls.
    pass
