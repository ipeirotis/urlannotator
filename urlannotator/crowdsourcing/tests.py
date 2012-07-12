import unittest

from  urlannotator.crowdsourcing.quality.algorithms import MajorityVoting


class MajorityVotingTest(unittest.TestCase):
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
