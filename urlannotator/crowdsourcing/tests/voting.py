from django.contrib.auth.models import User
from django.test import TestCase

from urlannotator.crowdsourcing.quality.algorithms import (MajorityVoting,
    DBVotesStorage, VotesStorage, ChainedVotesStorage)
from urlannotator.main.models import (LABEL_YES, LABEL_NO, Job, Worker, Sample,
    LABEL_BROKEN)
from urlannotator.flow_control.test import ToolsMockedMixin


class MajorityVotingTest(ToolsMockedMixin, TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

        self.workers = [Worker.objects.create_tagasauris(external_id=x)
            for x in xrange(20)]
        self.sample = Sample.objects.all()[0]

    def test_(self):
        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )
        mv.add_votes([])
        self.assertEqual([], mv.extract_decisions())

        mv.add_vote(
            worker_id=self.workers[2].id,
            object_id=self.sample.id,
            label=LABEL_YES,
        )
        self.assertEqual(LABEL_YES, mv.extract_decisions()[0][1])

        mv.add_votes([
            (self.workers[0].id, self.sample.id, LABEL_NO),
            (self.workers[1].id, self.sample.id, LABEL_NO)
        ])
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        mv.reset()
        self.assertEqual([], mv.extract_decisions())

        mv.add_votes([
            (self.workers[0].id, self.sample.id, LABEL_YES),
            (self.workers[1].id, self.sample.id, LABEL_YES),
            (self.workers[2].id, self.sample.id, LABEL_NO),
            (self.workers[3].id, self.sample.id, LABEL_NO),
            (self.workers[4].id, self.sample.id, LABEL_BROKEN),
            (self.workers[5].id, self.sample.id, LABEL_BROKEN),
            (self.workers[6].id, self.sample.id, LABEL_NO),
            (self.workers[7].id, self.sample.id, LABEL_NO),
            (self.workers[8].id, self.sample.id, LABEL_NO),
        ])
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

    def testProcessingVotes(self):
        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )

        worker = Worker.objects.create_odesk(external_id=1)
        Sample.objects.create_by_worker(
            url="http://google.com",
            source_val=self.workers[0].id,
            job_id=self.job.id,
        )
        sample = Sample.objects.get(job=self.job, url='http://google.com')

        mv.add_votes([
            (self.workers[0].id, self.sample.id, LABEL_YES),
            (self.workers[1].id, self.sample.id, LABEL_YES),
            (self.workers[2].id, self.sample.id, LABEL_NO),
            (self.workers[3].id, self.sample.id, LABEL_NO),
            (self.workers[4].id, self.sample.id, LABEL_BROKEN),
            (self.workers[5].id, self.sample.id, LABEL_BROKEN),
            (self.workers[6].id, self.sample.id, LABEL_NO),
            (self.workers[7].id, self.sample.id, LABEL_NO),
            (self.workers[8].id, self.sample.id, LABEL_NO),
        ])
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        votes = [
            (worker.id, sample.id, LABEL_YES),
            (self.workers[9].id, sample.id, LABEL_YES),
            (self.workers[10].id, sample.id, LABEL_YES),
        ]
        mv.add_votes(votes)
        self.assertEqual(mv.extract_decisions()[1][1], LABEL_YES)
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        votes = [
            (self.workers[11].id, sample.id, LABEL_NO),
            (self.workers[12].id, sample.id, LABEL_YES),
            (self.workers[13].id, sample.id, LABEL_YES),
        ]
        mv.add_votes(votes)
        self.assertEqual(mv.extract_decisions()[1][1], LABEL_YES)
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

        votes = [
            (self.workers[14].id, sample.id, LABEL_NO),
            (self.workers[15].id, sample.id, LABEL_NO),
            (self.workers[16].id, sample.id, LABEL_YES),
            (self.workers[17].id, sample.id, LABEL_YES),
            (self.workers[18].id, sample.id, LABEL_YES),
            (self.workers[19].id, sample.id, LABEL_YES),
        ]
        mv.add_votes(votes)
        self.assertEqual(mv.extract_decisions()[1][1], LABEL_YES)
        self.assertEqual(LABEL_NO, mv.extract_decisions()[0][1])

    def testQualityComputing(self):
        Sample.objects.create_by_worker(
            url="http://google.com",
            source_val=self.workers[0].id,
            job_id=self.job.id,
        )
        Sample.objects.create_by_worker(
            url="http://google.com/2",
            source_val=self.workers[1].id,
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
                votes.append((worker.id, sample1.id, LABEL_YES))
                votes.append((worker.id, sample2.id, LABEL_NO))
            elif res == 1:
                votes.append((worker.id, sample1.id, LABEL_YES))
                votes.append((worker.id, sample2.id, LABEL_NO))
            elif res == 2:
                votes.append((worker.id, sample1.id, LABEL_NO))
                votes.append((worker.id, sample2.id, LABEL_YES))
        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )
        mv.add_votes(votes)
        mv.extract_decisions()
        for worker in self.workers:
            res = worker.id % 3
            if res == 0:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    1,
                )
            elif res == 1:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    1,
                )
            elif res == 2:
                self.assertEqual(
                    worker.get_estimated_quality_for_job(self.job),
                    0,
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
                votes.append((worker.id, sample1.id, LABEL_YES))
                votes.append((worker.id, sample2.id, LABEL_NO))
            elif res == 1:
                votes.append((worker.id, sample1.id, LABEL_YES))
                votes.append((worker.id, sample2.id, LABEL_NO))
            elif res == 0:
                votes.append((worker.id, sample1.id, LABEL_NO))
                votes.append((worker.id, sample2.id, LABEL_YES))
        mv = MajorityVoting(
            job_id=self.job.id,
            votes_storage=DBVotesStorage(storage_id=self.job.id),
        )
        mv.add_votes(votes)
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


class ChainedVotesStorageTests(ToolsMockedMixin, TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': LABEL_YES}])

        self.workers = [Worker.objects.create_tagasauris(external_id=x)
            for x in xrange(20)]
        self.sample = Sample.objects.all()[0]

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
