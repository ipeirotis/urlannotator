class MajorityVoting(object):
    """
    Simple majority voting algorithm.
    """

    def __init__(self):
        self.votes = []

    def add_vote(self, vote):
        self.votes.append(vote)

    def add_votes(self, votes):
        self.votes += votes

    def clear(self):
        self.votes = []

    def get_majority(self):
        counter = 0
        candidate = None

        for v in self.votes:
            if counter == 0:
                candidate = v
                counter += 1
            elif v == candidate:
                counter += 1
            else:
                counter -= 1

        return candidate
