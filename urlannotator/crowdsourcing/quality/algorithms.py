from collections import Counter


class CrowdsourcingQualityAlgorithm(object):

    def __init__(self, job_id):
        ''' That job id will be needed in some cases - like in Troia
        '''
        self.job_id = job_id

    def add_vote(self, worker_id, object_id, label):
        ''' adds vote from given worker that was assigned to given object
        '''

    def add_votes(self, votes):
        ''' Default implementation '''
        for worker_id, object_id, label in votes:
            self.add_vote(worker_id, object_id, label)

    def reset(self):
        ''' Clears all stored votes and helper data
        '''

    def extract_decisions(self):
        ''' Should return predicted labels for objects in form:
            [(object_id, label), (object_id, label), ...]
        '''


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
