from collections import Counter


class MajorityVoting(object):
    """
    Simple majority voting algorithm.
    """

    def __init__(self):
        self.votes = []

    def process_votes(self, votes):
        map(self.add_vote, (v.label for v in votes))
        return self.get_majority()

    def add_vote(self, vote):
        self.votes.append(vote)

    def add_votes(self, votes):
        self.votes += votes

    def clear(self):
        self.votes = []

    def get_majority(self):
        if self.votes != []:
            return Counter(self.votes).most_common(1)[0][0]
        return None
