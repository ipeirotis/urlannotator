import json

from django.conf import settings

from urlannotator.classification.models import Classifier, TrainingSet
from urlannotator.main.models import Job
from urlannotator.classification.classifiers import (SimpleClassifier,
    GooglePredictionClassifier, Classifier247)

classifier_factory = None


def InvalidClassifier(name, **kwargs):
    print 'Unhandled classifier', name


def SimpleClassifier_init(entry, *args, **kwargs):
    entry.type = 'SimpleClassifier'
    params = {
        'training_set': 0,
    }
    entry.parameters = json.dumps(params)


def GooglePredictionClassifier_init(entry, prefix, job, *args, **kwargs):
    entry.type = 'GooglePredictionClassifier'
    params = {
        'model': '%sjob-%d' % (prefix, job.id),
        'training': 'RUNNING',
        'training_set': 0,
    }
    entry.parameters = json.dumps(params)


def Classifier247_init(entry, prefix, job, *args, **kwargs):
    entry.type = 'Classifier247'
    # Prefixes for subclassifiers' names
    prefix_a = ''.join([prefix, 'a-'])
    prefix_b = ''.join([prefix, 'b-'])

    # Create default classifier entries as subclassifiers
    classifier_name = settings.TWENTYFOUR_DEFAULT_CLASSIFIER
    classifier_A = classifier_factory.initialize_classifier(
        job_id=job.id,
        main=False,
        prefix=prefix_a,
        classifier_name=classifier_name,
        *args, **kwargs
    )
    classifier_B = classifier_factory.initialize_classifier(
        job_id=job.id,
        main=False,
        prefix=prefix_b,
        classifier_name=classifier_name,
        *args, **kwargs
    )
    params = {
        'switched': False,
        'training_set': 0,
        'classifier_A': classifier_A,
        'classifier_B': classifier_B,
    }
    entry.parameters = json.dumps(params)

# Contains mapping Classifier_name -> initialization_function.
classifier_inits = {
    'SimpleClassifier': SimpleClassifier_init,
    'GooglePredictionClassifier': GooglePredictionClassifier_init,
    'Classifier247': Classifier247_init,
}


def SimpleClassifer_ctor(job, entry, *args, **kwargs):
    classifier = SimpleClassifier(job.description, ['Yes', 'No'])
    classifier.id = entry.id
    training_set = TrainingSet.objects.newest_for_job(job)
    classifier.train(set_id=training_set.id)
    return classifier


def GooglePredictionClassifer_ctor(job, entry, *args, **kwargs):
    classifier = GooglePredictionClassifier(
        job.description,
        ['Yes', 'No'],
    )
    params = entry.parameters
    classifier.model = params['model']
    classifier.id = entry.id
    return classifier


def Classifier247_ctor(job, entry, *args, **kwargs):
    entry_A = entry.parameters['classifier_A']
    entry_B = entry.parameters['classifier_B']

    # First, create subclassfiers.
    classifier_A = classifier_factory.create_classifier_from_id(
        class_id=entry_A,
        *args, **kwargs
    )
    classifier_B = classifier_factory.create_classifier_from_id(
        class_id=entry_B,
        *args, **kwargs
    )
    classifier = Classifier247(classifier_A, classifier_B)
    if entry.parameters['switched']:
        classifier.switch()

    return classifier


# Contains mapping Classifier_name -> constructor_function.
classifier_ctors = {
    'SimpleClassifier': SimpleClassifer_ctor,
    'GooglePredictionClassifier': GooglePredictionClassifer_ctor,
    'Classifier247': Classifier247_ctor,
}


class ClassifierFactory(object):
    def initialize_classifier(self, job_id, classifier_name, main=True,
        prefix='', *args, **kwargs):
        """
            Manages initialization of a NEW classifier.
        """
        job = Job.objects.get(id=job_id)
        classifier_entry = Classifier(job=job, main=main)

        fun = classifier_inits.get(classifier_name, InvalidClassifier)
        fun(
            entry=classifier_entry,
            prefix=prefix,
            job=job,
            factory=self,
        )

        classifier_entry.save()

        if main:
            job.set_classifier_created()
        return classifier_entry.id

    def create_classifier(self, job_id, *args, **kwargs):
        '''
            Creates a classifier object from a main classifier tied to the job.
        '''
        # Custom classifier initialization
        job = Job.objects.get(id=job_id)
        classifier_entry = Classifier.objects.get(job=job, main=True)

        ctor = classifier_ctors.get(classifier_entry.type, InvalidClassifier)
        classifier = ctor(
            job=job,
            entry=classifier_entry,
            name=classifier_entry.type,
            factory=self,
        )
        return classifier

    def create_classifier_from_id(self, class_id, *args, **kwargs):
        '''
            Creates a classifier object from an entry with given id.
        '''
        entry = Classifier.objects.get(id=class_id)
        ctor = classifier_ctors.get(entry.type, InvalidClassifier)
        classifier = ctor(
            job=entry.job,
            entry=entry,
            name=entry.type,
        )
        return classifier

classifier_factory = ClassifierFactory()
