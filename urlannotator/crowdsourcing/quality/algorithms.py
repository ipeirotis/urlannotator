from collections import Counter


class VotesStorage(object):

    def __init__(self, storage_id):
        ''' In our case storage_id == job_id
        '''
        self.storage_id = storage_id

    def add_vote(self, worker_id, object_id, label):
        ''' adds vote from given worker that was assigned to given object
        Should ignore repeated votes
        '''

    def add_votes(self, votes):
        ''' Default implementation '''
        for worker_id, object_id, label in votes:
            self.add_vote(worker_id, object_id, label)

    def reset(self):
        ''' Clears all stored votes and helper data
        '''

    def get_all_votes(self):
        ''' Should return all votes in form:
            [(worker_id, object_id, label), ...]
        '''


class CrowdsourcingQualityAlgorithm(object):
    ''' We here wraps VotesStorage because we sometimes would like to do some
    calculations to make extract_decisions work faster
    '''

    def __init__(self, job_id, votes_storage):
        ''' That job id will be needed in some cases - like in Troia
        '''
        self.job_id = job_id
        self.votes_storage = votes_storage

    def add_vote(self, worker_id, object_id, label):
        self.votes_storage.add_vote(worker_id, object_id, label)

    def add_votes(self, votes):
        self.votes_storage.add_votes(votes)

    def reset(self):
        self.votes_storage.reset()

    def extract_decisions(self):
        ''' Should return predicted labels for objects in form:
            [(object_id, label), (object_id, label), ...]

            In most cases it will use votes_storage.get_all_votes
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
