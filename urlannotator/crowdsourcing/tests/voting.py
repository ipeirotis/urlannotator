from django.contrib.auth.models import User
from django.test import TestCase

from urlannotator.crowdsourcing.models import WorkerQualityVote
from urlannotator.crowdsourcing.quality.algorithms import (MajorityVoting,
    DBVotesStorage, VotesStorage, ChainedVotesStorage)
from urlannotator.main.models import (LABEL_YES, LABEL_NO, Job, Worker, Sample,
    LABEL_BROKEN, GoldSample, WORKER_TYPE_TAGASAURIS, WorkerJobAssociation)
from urlannotator.flow_control.test import ToolsMockedMixin


class MajorityVotingTest(ToolsMockedMixin, TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

        Worker.objects.bulk_create(
            Worker(external_id=x, worker_type=WORKER_TYPE_TAGASAURIS)
            for x in xrange(20)
        )
        self.workers = Worker.objects.all()
        WorkerJobAssociation.objects.bulk_create(
            WorkerJobAssociation(job=self.job, worker=w)
            for w in self.workers
        )

        self.sample = Sample.objects.create(
            job=self.job,
            url='10clouds.com')
        GoldSample.objects.create(sample=self.sample, label=LABEL_YES)

    def test_(self):
        def new_vote(worker, sample, label):
            return WorkerQualityVote(worker=worker, sample=sample, label=label)

        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )
        mv.add_votes([])
        self.assertEqual([], mv.extract_decisions())

        WorkerQualityVote.objects.create(
            worker=self.workers[2],
            sample=self.sample,
            label=LABEL_YES,
        )
        self.assertEqual(LABEL_YES, mv.extract_decisions()[0][1])

        WorkerQualityVote.objects.bulk_create([
            new_vote(self.workers[0], self.sample, LABEL_NO),
            new_vote(self.workers[1], self.sample, LABEL_NO)
        ])
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        mv.reset()
        self.assertEqual([], mv.extract_decisions())

        WorkerQualityVote.objects.bulk_create([
            new_vote(self.workers[0], self.sample, LABEL_YES),
            new_vote(self.workers[1], self.sample, LABEL_YES),
            new_vote(self.workers[2], self.sample, LABEL_NO),
            new_vote(self.workers[3], self.sample, LABEL_NO),
            new_vote(self.workers[4], self.sample, LABEL_BROKEN),
            new_vote(self.workers[5], self.sample, LABEL_BROKEN),
            new_vote(self.workers[6], self.sample, LABEL_NO),
            new_vote(self.workers[7], self.sample, LABEL_NO),
            new_vote(self.workers[8], self.sample, LABEL_NO),
        ])
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

    def testProcessingVotes(self):
        def new_vote(worker, sample, label):
            return WorkerQualityVote(worker=worker, sample=sample, label=label)

        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )

        worker = Worker.objects.create_tagasauris(external_id=21)
        WorkerJobAssociation.objects.create(job=self.job, worker=worker)

        Sample.objects.create_by_worker(
            url="http://google.com",
            source_val=self.workers[0].id,
            job_id=self.job.id,
        )
        sample = Sample.objects.get(job=self.job, url='http://google.com')

        WorkerQualityVote.objects.bulk_create([
            new_vote(self.workers[0], self.sample, LABEL_YES),
            new_vote(self.workers[1], self.sample, LABEL_YES),
            new_vote(self.workers[2], self.sample, LABEL_NO),
            new_vote(self.workers[3], self.sample, LABEL_NO),
            new_vote(self.workers[4], self.sample, LABEL_BROKEN),
            new_vote(self.workers[5], self.sample, LABEL_BROKEN),
            new_vote(self.workers[6], self.sample, LABEL_NO),
            new_vote(self.workers[7], self.sample, LABEL_NO),
            new_vote(self.workers[8], self.sample, LABEL_NO),
        ])
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        WorkerQualityVote.objects.bulk_create([
            new_vote(worker, sample, LABEL_YES),
            new_vote(self.workers[9], sample, LABEL_YES),
            new_vote(self.workers[10], sample, LABEL_YES),
        ])

        self.assertEqual(mv.extract_decisions()[1][1], LABEL_YES)
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        WorkerQualityVote.objects.bulk_create([
            new_vote(self.workers[11], sample, LABEL_NO),
            new_vote(self.workers[12], sample, LABEL_YES),
            new_vote(self.workers[13], sample, LABEL_YES),
        ])

        self.assertEqual(mv.extract_decisions()[1][1], LABEL_YES)
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        WorkerQualityVote.objects.bulk_create([
            new_vote(self.workers[14], sample, LABEL_NO),
            new_vote(self.workers[15], sample, LABEL_NO),
            new_vote(self.workers[16], sample, LABEL_YES),
            new_vote(self.workers[17], sample, LABEL_YES),
            new_vote(self.workers[18], sample, LABEL_YES),
            new_vote(self.workers[19], sample, LABEL_YES),
        ])

        self.assertEqual(mv.extract_decisions()[1][1], LABEL_YES)
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

    def testQualityComputing(self):
        def new_vote(worker, sample, label):
            return WorkerQualityVote(worker=worker, sample=sample, label=label)

        worker = Worker.objects.create_tagasauris(external_id=20)
        Sample.objects.create_by_worker(
            url="http://google.com",
            source_val=worker.id,
            job_id=self.job.id,
        )
        Sample.objects.create_by_worker(
            url="http://google.com/2",
            source_val=worker.id,
            job_id=self.job.id,
        )
        sample1 = Sample.objects.get(job=self.job, url='http://google.com')
        sample2 = Sample.objects.get(job=self.job, url='http://google.com/2')
        votes = []
        # 20 workers, 3 different voting sets
        # 7 sets of type 1
        # 7 sets of type 2
        # 6 sets of type 3
        # = sample1's label is YES, sample2's label is NO
        for worker in self.workers:
            res = worker.id % 3
            if res == 0:
                votes.append(new_vote(worker, sample1, LABEL_YES))
                votes.append(new_vote(worker, sample2, LABEL_NO))
            elif res == 1:
                votes.append(new_vote(worker, sample1, LABEL_YES))
                votes.append(new_vote(worker, sample2, LABEL_NO))
            elif res == 2:
                votes.append(new_vote(worker, sample1, LABEL_NO))
                votes.append(new_vote(worker, sample2, LABEL_YES))

        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )

        WorkerQualityVote.objects.bulk_create(votes)
        mv.extract_decisions()
        for worker in self.workers:
            res = worker.id % 3
            if res == 0:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    1.0,
                )
            elif res == 1:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    1.0,
                )
            elif res == 2:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    0.0,
                )
        # Check if different votes processing properly clean themselves.
        mv.reset()
        votes = []
        # 20 workers, 3 different voting sets
        # 6 sets of type 1
        # 7 sets of type 2
        # 7 sets of type 3
        # = sample1's label is YES, sample2's label is NO
        for worker in self.workers:
            res = worker.id % 3
            if res == 2:
                votes.append(new_vote(worker, sample1, LABEL_YES))
                votes.append(new_vote(worker, sample2, LABEL_NO))
            elif res == 1:
                votes.append(new_vote(worker, sample1, LABEL_YES))
                votes.append(new_vote(worker, sample2, LABEL_NO))
            elif res == 0:
                votes.append(new_vote(worker, sample1, LABEL_NO))
                votes.append(new_vote(worker, sample2, LABEL_YES))

        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )

        WorkerQualityVote.objects.bulk_create(votes)
        mv.extract_decisions()
        for worker in self.workers:
            res = worker.id % 3
            if res == 2:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    1,
                )
            elif res == 1:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    1,
                )
            elif res == 0:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    0,
                )


class DBStorageTest(ToolsMockedMixin, TestCase):
    def test_storage(self):
        worker = Worker.objects.create(external_id=1,
            worker_type=WORKER_TYPE_TAGASAURIS)
        u = User.objects.create_user(username='testing', password='test')

        job = Job.objects.create_active(
            account=u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

        sample = Sample.objects.create(job=job, url='10clouds.com')

        storage = DBVotesStorage(storage_id=job.id)
        storage.add_votes([(worker.id, sample.id, LABEL_YES)])

        self.assertEqual(WorkerQualityVote.objects.all().count(), 1)


class ChainedVotesStorageTests(ToolsMockedMixin, TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

        Worker.objects.bulk_create(
            Worker(external_id=x, worker_type=WORKER_TYPE_TAGASAURIS)
            for x in xrange(20)
        )
        self.workers = Worker.objects.all()
        WorkerJobAssociation.objects.bulk_create(
            WorkerJobAssociation(job=self.job, worker=w)
            for w in self.workers
        )

        self.sample = Sample.objects.create(
            job=self.job,
            url='10clouds.com')
        GoldSample.objects.create(sample=self.sample, label=LABEL_YES)

    def testChained(self):
        class RareFaultStorage(VotesStorage):
            def add_vote(self, worker_id, object_id, label):
                return object_id <= 2

            def add_votes(self, votes):
                return len(votes) <= 10

            def reset(self):
                return True

            def get_all_votes(self):
                return []

        class DummyStorage(VotesStorage):
            def add_vote(self, worker_id, object_id, label):
                return True

            def add_votes(self, votes):
                return True

            def reset(self):
                return True

            def get_all_votes(self):
                return [(100000, 'Weeeeee')]

        storages = [
            RareFaultStorage(storage_id=self.job.id),
            DummyStorage(storage_id=self.job.id),
            DBVotesStorage(storage_id=self.job.id),
        ]
        cvs = ChainedVotesStorage(storages)
        cvs.add_vote(
            worker_id=self.workers[0].id,
            object_id=self.sample.id,
            label=LABEL_YES,
        )

        self.assertEqual(storages[2].get_all_votes(),
            [(self.workers[0].id, self.sample.id, LABEL_YES)])
        cvs.reset()

        votes = [
            (self.workers[11].id, self.sample.id, LABEL_YES),
            (self.workers[1].id, self.sample.id, LABEL_YES),
            (self.workers[2].id, self.sample.id, LABEL_YES),
            (self.workers[3].id, self.sample.id, LABEL_YES),
            (self.workers[4].id, self.sample.id, LABEL_YES),
            (self.workers[5].id, self.sample.id, LABEL_YES),
            (self.workers[6].id, self.sample.id, LABEL_YES),
            (self.workers[7].id, self.sample.id, LABEL_YES),
            (self.workers[8].id, self.sample.id, LABEL_YES),
            (self.workers[9].id, self.sample.id, LABEL_YES),
            (self.workers[10].id, self.sample.id, LABEL_YES),
        ]
        cvs.add_votes(votes=votes)
        self.assertEqual(storages[2].get_all_votes(), [])

        cvs.add_votes(votes=votes[9:])
        all_votes = set()
        for storage in storages:
            for vote in storage.get_all_votes():
                all_votes.add(vote)

        self.assertEqual(list(all_votes), cvs.get_all_votes())
