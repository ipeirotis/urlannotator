from urlannotator.payments.models import (PAYMENT_STATUS_COMPLETED,
    WorkerPayment, JobPaymentSettings, task_to_name, JOB_TASK_BTM,
    JOB_TASK_VOTING, JOB_TASK_SAMPLE_GATHERING)


class PaymentBackend(object):
    def issue_payment(self, payment):
        """
            Issues a payment to be completed. Does the actual logic that
            sends the payment to the worker using whatever
            specific API/Platform.
            Returns True on success.
        """
        raise NotImplementedError()

    def init_job(self, job):
        """
            Initializes payment backend for given job.
        """
        raise NotImplementedError()

    def charge_owner(self, job):
        """
            Charges job owner's account for job's budget, so we have funds to
            use.
        """
        raise NotImplementedError()

    def join_budgets(self, budget1, budget2):
        """
            Joins to budget splits due to more than one owner's charging.
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

    def get_split_budget(self, job):
        """
            Returns budget split into each task's budget.
        """
        settings = job.jobpaymentsettings_set.get(backend=self.backend_name)
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

    def issue_payment(self, payment):
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

    def get_payment_status(self, payment):
        return payment.status
