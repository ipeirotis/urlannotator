from django.db import IntegrityError

from urlannotator.crowdsourcing.models import WorkerQualityVote
from urlannotator.main.models import (Sample, Worker, LABEL_YES, LABEL_NO,
    LABEL_BROKEN, Job, WorkerJobAssociation, GoldSample)


class VotesStorage(object):

    def __init__(self, storage_id):
        ''' In our case storage_id == job_id
        '''
        self.storage_id = storage_id

    def add_vote(self, worker_id, object_id, label):
        ''' adds vote from given worker that was assigned to given object
            Should ignore repeated votes. Returns True on success.
        '''

    def add_gold_vote(self, object_id, label):
        '''
            Adds gold vote. Returns True on success.
        '''

    def add_gold_votes(self, votes):
        '''
            Votes is a list of 2-tuples (object_id, label).
            Adds gold votes. Returns True on success.
        '''
        for object_id, label in votes:
            self.add_vote(object_id=object_id, label=label)

    def add_votes(self, votes):
        ''' Default implementation.

            Votes is a list of 3-tuples (worker_id, object_id, label).
            Returns True on success.
        '''
        for worker_id, object_id, label in votes:
            self.add_vote(worker_id, object_id, label)

    def reset(self):
        ''' Clears all stored votes and helper data
        '''

    def get_all_votes(self):
        ''' Should return all votes in form:
            [(worker_id, object_id, label), ...]
        '''


class DBVotesStorage(VotesStorage):
    def add_vote(self, worker_id, object_id, label):
        worker = Worker.objects.get(id=worker_id)
        sample = Sample.objects.get(id=object_id)
        try:
            WorkerQualityVote.objects.new_vote(
                worker=worker,
                sample=sample,
                label=label,
            )
            return True
        except IntegrityError:
            # Skip duplicates
            return False

    def reset(self):
        super(DBVotesStorage, self).reset()
        ids = WorkerQualityVote.objects.filter(btm_vote=False).select_related(
            'sample')
        ids = [w.id for w in ids if w.sample.job_id == self.storage_id]
        WorkerQualityVote.objects.filter(id__in=ids).delete()

    def get_all_votes(self):
        ids = WorkerQualityVote.objects.filter(btm_vote=False).select_related(
            'sample')
        return [(w.worker_id, w.sample_id, w.label)
            for w in ids if w.sample.job_id == self.storage_id]


class TroiaDBStorage(VotesStorage):
    def __init__(self, storage_id):
        super(TroiaDBStorage, self).__init__(storage_id=storage_id)
        self.tc = TroiaClient(settings.TROIA_HOST, None)

    def add_vote(self, worker_id, object_id, label):
        pass

    def reset(self):
        super(DBVotesStorage, self).reset()
        ids = WorkerQualityVote.objects.filter(btm_vote=False).select_related(
            'sample')
        ids = [w.id for w in ids if w.sample.job_id == self.storage_id]
        WorkerQualityVote.objects.filter(id__in=ids).delete()

    def get_all_votes(self):
        ids = WorkerQualityVote.objects.filter(btm_vote=False).select_related(
            'sample')
        return [(w.worker_id, w.sample_id, w.label)
            for w in ids if w.sample.job_id == self.storage_id]


class ChainedVotesStorage(VotesStorage):
    """
        Allows chaining multiple votes storages. Methods are executed on
        the storages in the same order they were given.
    """
    def __init__(self, storages):
        self.storages = storages

    def _execute_on_all(self, function_name, kwargs={}):
        """
            Executes every storages' method named `function_name` with `kwargs`
        """
        for storage in self.storages:
            func = getattr(storage, function_name)
            if func(**kwargs) is False:
                return False
        return True

    def add_vote(self, worker_id, object_id, label):
        return self._execute_on_all('add_vote', {
            'worker_id': worker_id,
            'object_id': object_id,
            'label': label,
        })

    def add_votes(self, votes):
        return self._execute_on_all('add_votes', {
            'votes': votes,
        })

    def reset(self):
        return self._execute_on_all('reset')

    def get_all_votes(self):
        votes_set = set()
        map(
            lambda storage: map(
                lambda vote: votes_set.add(vote),
                storage.get_all_votes()
            ),
            self.storages
        )

        return list(votes_set)


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

            In most cases it will use votes_storage.get_all_votes.
            Should also handle worker quality.
        '''

    def calculate_workers_quality(self, data):
        """
            Calculates each workers' quality for appriopriate jobs based on
            passed data.
            Data should be in format used by `extract_decisions`.
        """
        def samples_generator():
            for vote in data:
                yield vote[0]

        jobs_set = set()
        samples = Sample.objects.in_bulk(samples_generator)
        map(
            lambda sample: jobs_set.add(sample[1].job_id),
            samples.iteritems()
        )
        # Clear all entries to be ready to recompute them
        for job in Job.objects.filter(id__in=jobs_set).select_related('workerjobassociation_set').iterator():
            job.workerjobassociation_set.update(data={})

        assoc_set = set()
        for sample_id, correct_label in data:
            sample = samples[sample_id]
            votes = sample.workerqualityvote_set.all().iterator()
            for vote in votes:
                assoc = WorkerJobAssociation.objects.get(
                    job_id=sample.job_id,
                    worker_id=vote.worker_id,
                )
                assoc.data['all_votes'] = assoc.data.get('all_votes', 0) + 1
                if vote.label == correct_label:
                    correct = assoc.data.get('correct_labels', 0)
                    assoc.data['correct_labels'] = correct + 1
                assoc.save()
                assoc_set.add(assoc.id)

        for assoc in WorkerJobAssociation.objects.filter(id__in=assoc_set).iterator():
            assoc.data['estimated_quality'] = self.calculate_quality(assoc=assoc)
            assoc.save()


class MajorityVoting(CrowdsourcingQualityAlgorithm):
    """
    Simple majority voting algorithm.
    """

    def calculate_quality(self, assoc):
        if not assoc.data['all_votes']:
            return 0

        return assoc.data.get('correct_labels', 0) / assoc.data['all_votes']

    def extract_decisions(self):
        votes = {}
        for worker_id, object_id, label in self.votes_storage.get_all_votes():
            counts = votes.get(object_id, {
                LABEL_YES: 0,
                LABEL_NO: 0,
                LABEL_BROKEN: 0,
            })
            gold = GoldSample.objects.filter(sample_id=object_id)

            # Gold samples can't change their label.
            if gold:
                counts[gold[0].label] = 1000
                continue

            if label == LABEL_YES:
                count = counts.get(LABEL_YES, 0)
                counts[LABEL_YES] = count + 1
            elif label == LABEL_NO:
                count = counts.get(LABEL_NO, 0)
                counts[LABEL_NO] = count + 1
            elif label == LABEL_BROKEN:
                count = counts.get(LABEL_BROKEN, 0)
                counts[LABEL_BROKEN] = count + 1

            votes[object_id] = counts
            WorkerQualityVote.objects.filter(
                worker=worker_id,
                sample=object_id,
            ).update(is_new=False)

        decisions = [(el, max(val.iteritems(), key=lambda x: x[1])[0])
            for el, val in votes.iteritems()]
        self.calculate_workers_quality(data=decisions)

        return decisions
