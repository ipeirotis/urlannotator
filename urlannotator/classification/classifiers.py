import nltk
import httplib2
import os
import csv
import json

from apiclient.discovery import build
from boto.gs.connection import GSConnection
from boto.gs.bucket import Bucket
from django.conf import settings
from oauth2client.file import Storage
from boto.s3.key import Key

from urlannotator.classification.models import Classifier as ClassifierModel
from urlannotator.tools.synchronization import RWSynchronize247


class Classifier247(RWSynchronize247):

    def __init__(self, reader_instance, writer_instance):
        """
        Our permanent (24/7) synchronize template can be initialized with
        instances of sync objects.
        """

        writer_functions = [
            'train',
            'update'
        ]

        reader_functions = [
            'classify',
            'classify_with_info'
        ]

        super(self.__class__, self).__init__('Classifier247',
            reader_instance=reader_instance,
            writer_instance=writer_instance,
            reader_functions=reader_functions,
            writer_functions=writer_functions)


class Classifier(object):
    def train(self, samples):
        pass

    def update(self, samples):
        pass

    def classify(self, sample):
        pass

    def classify_with_info(self, sample):
        pass


class SimpleClassifier(Classifier):
    """
        Simple url classifier using Decision Tree
    """

    def __init__(self, description, classes, *args, **kwargs):
        """
            Description and classes are not used by this classifier.
        """
        self.classifier = None
        super(SimpleClassifier, self).__init__(*args, **kwargs)

    @staticmethod
    def get_features(sample):
        """
            Creates a set of words the sample's text consists of.
        """
        if not hasattr(sample, 'text') and hasattr(sample, 'sample'):
            sample = sample.sample

        words = nltk.word_tokenize(sample.text)
        words = set(words)
        feature_set = {}
        for word in words:
            feature_set[word] = True
        return feature_set

    def train(self, samples):
        """
            Trains classifier on gives samples' set. If sample has no label,
            it's checked for being a GoldSample.
        """
        train_set = []
        for sample in samples:
            job = sample.sample.job
            sample.sample.label = sample.label
            train_set.append((self.get_features(sample.sample), sample.label))
        if train_set:
            self.classifier = nltk.classify.DecisionTreeClassifier.train(
                train_set)
            job.set_classifier_trained()

    def classify(self, sample):
        """
            Classifies gives sample and saves result to the model.
        """
        if self.classifier is None:
            return None
        if not hasattr(sample, 'text'):
            sample = sample.sample
        label = self.classifier.classify(self.get_features(sample))
        sample.label = label
        sample.save()
        return label

    def classify_with_info(self, sample):
        """
            Classifies given sample and returns more detailed data.
            Currently only label.
        """
        if self.classifier is None:
            return None
        label = self.classifier.classify(self.get_features(sample.sample))
        sample.label = label
        sample.save()
        return {'label': label}

# Google Storage parameters used in GooglePrediction classifier
GOOGLE_STORAGE_PREFIX = 'gs'
GOOGLE_BUCKET_NAME = 'urlannotator'


class GooglePredictionClassifier(Classifier):
    """
        Classifier using Google Prediction API
    """

    def __init__(self, description, classes, *args, **kwargs):
        """
            Description and classes are not used by this classifier.
        """
        self.model = None
        storage = Storage('prediction.dat')
        credentials = storage.get()

        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our good Credentials.
        http = httplib2.Http()
        http = credentials.authorize(http)

        # Get access to the Prediction API.
        service = build("prediction", "v1.5", http=http)
        self.papi = service.trainedmodels()

    def analyze(self):
        try:
            status = self.papi.analyze(id=self.model).execute()
            return status
        except:
            return {}

    def get_train_status(self):
        try:
            status = self.papi.get(id=self.model).execute()
            return status['trainingStatus']
        except:
            # Model doesn't exist (first training).
            return 'RUNNING'

    def create_and_upload_training_data(self, samples):
        training_dir = 'urlannotator-training-data'
        file_name = 'model-%s' % self.model
        file_out = '%s/%s.csv' % (training_dir, file_name)

        # Lets create dir for temporary training sets.
        os.system("mkdir -p %s" % training_dir)

        # Write data to csv file
        data = open(file_out, 'wb')
        writer = csv.writer(data)
        for sample in samples:
            writer.writerow(['%s' % sample.label, '"%s"' % sample.text])
        data.close()

        # Upload file to gs
        training_file = open(file_out, 'r')

        con = GSConnection(settings.GS_ACCESS_KEY, settings.GS_SECRET)
        try:
            bucket = con.create_bucket(GOOGLE_BUCKET_NAME)
        except:
            # Bucket exists
            bucket = Bucket(connection=con, name=GOOGLE_BUCKET_NAME)

        key = Key(bucket)
        key.key = file_name
        key.set_contents_from_file(training_file)
        training_file.close()

        key.make_public()
        # Remove file from disc
        os.system('rm %s' % file_out)

        return file_name

    def train(self, samples):
        """
            Trains classifier on gives samples' set. If sample has no label,
            it's checked for being a GoldSample. Required model
            is TrainingSample.
        """
        # Turns off classifier for the job. Can't be used until classification
        # is done.
        entry = ClassifierModel.objects.get(id=self.id)
        job = entry.job
        job.unset_classifier_trained()

        train_set = []
        samp_num = 0
        for sample in samples:
            samp_num += 1
            sample.sample.label = sample.label
            train_set.append(sample.sample)

        name = self.create_and_upload_training_data(train_set)
        body = {
            'id': self.model,
            'storageDataLocation': 'urlannotator/%s' % name
        }

        # We have to always check for training status due to different
        # instances of the classifier in different threads. YET only one is
        # used at a time.
        try:
            status = self.papi.get(id=self.model).execute()
            if status['trainingStatus'] == 'DONE':
                self.papi.update(body=body).execute()
        except:
            # Model doesn't exist (first training).
            self.papi.insert(body=body).execute()

        # Update classifier entry.
        params = entry.parameters
        params['training'] = 'RUNNING'
        entry.parameters = json.dumps(params)
        entry.save()

    def classify(self, sample):
        """
            Classifies given sample and saves result to the model.
        """
        if self.model is None:
            return None

        body = {'input': {'csvInstance': [sample.sample.text]}}
        label = self.papi.predict(body=body, id=self.model).execute()
        sample.label = label['outputLabel']
        sample.label_probability = label['outputMulti']
        sample.save()

        return label['outputLabel']

    def classify_with_info(self, sample):
        """
            Classifies given sample and returns more detailed data.
            Currently only label.
        """
        if self.model is None:
            return None

        body = {'input': {'csvInstance': [sample.sample.text]}}
        label = self.papi.predict(body=body, id=self.model).execute()
        sample.label = label['outputLabel']
        sample.label_probability = label['outputMulti']
        sample.save()

        result = {
            'outputLabel': label['outputLabel'],
            'outputMulti': label['outputMulti']
        }
        return result
