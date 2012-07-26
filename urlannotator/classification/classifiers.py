import nltk
import httplib2
import os
import csv
import boto

from apiclient.discovery import build
from django.conf import settings
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from tenclouds.lock.rwlock import MemcachedRWLock
from tenclouds.lock.locks import MemcacheLock

from urlannotator.main.models import Sample, GoldSample


class Classifier247(object):

    def __init__(self, classifier_cls, rwlock_cls=MemcachedRWLock,
            lock_cls=MemcacheLock, *args, **kwargs):
        """
        Our permanent (24/7) classifier can be initialized with custom
        classifier class - classifier_cls (which performs real classification) &
        with custom locking implementation. On default we use MamcacheLock and
        MemcachedRWLock.
        """

        self.lock = lock_cls()
        self.rwlock = rwlock_cls()
        self.read_classifier = classifier_cls(*args, **kwargs)
        self.write_classifier = classifier_cls(*args, **kwargs)

    def train(self, *args, **kwargs):
        """
        Writing task. Lock write classifier.
        On default after training switch is performed. This can be disabled by
        passing switch=False in kwargs.
        """

        # Switch can be disabled.
        switch = True
        if 'switch' in kwargs:
            switch = kwargs['switch']
            kwargs.pop('switch')

        self.lock.acquire()
        result = self.write_classifier.train(*args, **kwargs)
        if switch:
            self._switch_with_lock()
        self.lock.release()

        return result

    def update(self, *args, **kwargs):
        """ Writing task. Lock write classifier.
        """

        self.lock.acquire()
        result = self.write_classifier.update(*args, **kwargs)
        self.lock.release()

        return result

    def classify(self, *args, **kwargs):
        """ Reading task. Read classifier is used - aquire reader rwlock.
        """

        self.rwlock.reader_acquire()
        result = self.read_classifier.classify(*args, **kwargs)
        self.rwlock.reader_release()

        return result

    def classify_with_info(self, *args, **kwargs):
        """ Reading task. Read classifier is used - aquire reader rwlock.
        """

        self.rwlock.reader_acquire()
        result = self.read_classifier.classify_with_info(*args, **kwargs)
        self.rwlock.reader_release()

        return result

    def switch(self):
        """
        Cold switch. Aquires all locks and runs switch. In result whole
        classifier is blocked for switch time.
        """

        self.lock.acquire()
        self._switch_with_lock()
        self.lock.release()

    def _switch_with_lock(self):
        """
        Hot switch. Use only when ensured that write classifier is not used.
        F.e. when training task ends.
        """

        self.rwlock.writer_acquire()
        (self.read_classifier, self.write_classifier) = (self.write_classifier,
            self.read_classifier)
        self.rwlock.writer_release()


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
            if not isinstance(sample, Sample):
                continue
            if sample.label == '':
                try:
                    gold_sample = GoldSample.objects.get(sample=sample)
                    sample.label = gold_sample.label
                except:
                    continue
            train_set.append((self.get_features(sample), sample.label))
        if train_set:
            self.classifier = nltk.classify.DecisionTreeClassifier.train(
                train_set)

    def classify(self, sample):
        """
            Classifies gives sample and saves result to the model.
        """
        if self.classifier is None:
            return None
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
        label = self.classifier.classify(self.get_features(sample))
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
        flow = OAuth2WebServerFlow(
            '382637721312.apps.googleusercontent.com',
            'Y-MqDvcWxf4em0DrKYKK7CSv',
            'https://www.googleapis.com/auth/prediction',
            None,  # user_agent
            'https://accounts.google.com/o/oauth2/auth',
            'https://accounts.google.com/o/oauth2/token')

        storage = Storage('prediction.dat')
        credentials = storage.get()

        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our good Credentials.
        http = httplib2.Http()
        http = credentials.authorize(http)

        # Get access to the Prediction API.
        service = build("prediction", "v1.5", http=http)
        self.papi = service.trainedmodels()

    def create_and_upload_training_data(self, samples):
        training_dir = 'urlannotator-training-data'
        file_name = 'job-%d' % self.model
        file_out = '%s/%s.csv' % (training_dir, file_name)

        # Write data to csv file
        writer = csv.writer(open(file_out, 'wb'))
        for sample in samples:
            writer.writerow([sample.text, sample.label])
        writer.close()

        # Upload file to gs
        training_file = open(file_out, 'r')
        upload_path = '%s/%s.csv' % (settings.GOOGLE_BUCKET_NAME, file_name)
        uri = boto.storage_uri(upload_path, settings.GOOGLE_STORAGE_PREFIX)
        uri.new_key().set_contents_from_file(training_file)
        training_file.close()

        # Remove file from disc
        os.system('rm %s' % file_out)

    def train(self, samples):
        """
            Trains classifier on gives samples' set. If sample has no label,
            it's checked for being a GoldSample.
        """
        train_set = []
        for sample in samples:
            if not isinstance(sample, Sample):
                continue
            if sample.label == '':
                try:
                    gold_sample = GoldSample.objects.get(sample=sample)
                    sample.label = gold_sample.label
                except:
                    continue
            train_set.append((self.get_features(sample), sample.label))
        # TODO: Send training set in csv to google storage.
        # self.create_and_upload_training_data(train_set)
        # TODO: Request classifier update

    def classify(self, sample):
        """
            Classifies gives sample and saves result to the model.
        """
        if self.model is None:
            return None

        # TODO: Uncomment when google storage has been set up and running
        # body = {'input': {'csvInstance': [sample.text]}}
        # label = self.papi.predict(body=body, id=self.model).execute()
        # label = label['outputLabel']

        label = 'Yes'
        sample.label = label
        sample.save()
        return label

    def classify_with_info(self, sample):
        """
            Classifies given sample and returns more detailed data.
            Currently only label.
        """
        if self.model is None:
            return None

        # TODO: Uncomment when google storage has been set up and running
        # body = {'input': {'csvInstance': [sample.text]}}
        # label = self.papi.predict(body=body, id=self.model).execute()
        # result = {
        #     'outputLabel': label['outputLabel'],
        #     'outputMulti': label['outputMulti']
        # }

        label = 'Yes'
        sample.label = label
        sample.save()
        result = {'outputLabel': label, 'outputMulti': {}}
        return result
