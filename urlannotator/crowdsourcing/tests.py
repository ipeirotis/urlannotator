from django.contrib.auth.models import User
from django.test import TestCase

from urlannotator.crowdsourcing.quality.algorithms import MajorityVoting
from urlannotator.crowdsourcing.models import WorkerQualityVote
from urlannotator.main.models import LABEL_YES, LABEL_NO, Job, Worker, Sample


class MajorityVotingTest(TestCase):

    def test_(self):
        mv = MajorityVoting()
        mv.add_votes([])
        self.assertEqual(None, mv.get_majority())

        mv.add_vote(1)
        self.assertEqual(1, mv.get_majority())

        mv.add_votes([2, 2])
        self.assertEqual(2, mv.get_majority())

        mv.clear()
        self.assertEqual(None, mv.get_majority())

        mv.add_votes([1, 1, 2, 2, 3, 3, 2, 2, 2])
        self.assertEqual(2, mv.get_majority())

    def testProcessingVotes(self):
        mv = MajorityVoting()

        worker = Worker.objects.create_odesk(external_id=1)
        user = User.objects.create_user("asd", "asd")
        job = Job.objects.create(
            account=user.get_profile()
        )
        sample = Sample.objects.create(
            source_val='asd',
            job=job,
            url=""
        )

        def newVote(label):
            return WorkerQualityVote.objects.new_vote(
                sample=sample,
                worker=worker,
                label=label
            )

        votes = [
            newVote(LABEL_YES),
            newVote(LABEL_YES),
            newVote(LABEL_YES),
        ]
        self.assertEqual(mv.process_votes(votes), LABEL_YES)

        votes = [
            newVote(LABEL_NO),
            newVote(LABEL_YES),
            newVote(LABEL_YES),
        ]
        self.assertEqual(mv.process_votes(votes), LABEL_YES)

        votes = [
            newVote(LABEL_NO),
            newVote(LABEL_NO),
            newVote(LABEL_YES),
            newVote(LABEL_YES),
            newVote(LABEL_YES),
        ]
        self.assertEqual(mv.process_votes(votes), LABEL_YES)
