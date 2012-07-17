import nltk

from tenclouds.lock.rwlock import MemcachedRWLock
from tenclouds.lock.locks import MemcacheLock

from urlannotator.main.models import Sample


class Classifier247(object):

    def __init__(self, classifier_cls, rwlock_cls=MemcachedRWLock,
            lock_cls=MemcacheLock):
        self.lock = lock_cls()
        self.rwlock = rwlock_cls()
        self.read_classifier = classifier_cls()
        self.write_classifier = classifier_cls()

    def train(self, *args, **kwargs):
        self.lock.acquire()
        result = self.write_classifier.train(*args, **kwargs)
        self.switch()
        self.lock.release()

        return result

    def update(self, *args, **kwargs):
        self.lock.acquire()
        result = self.write_classifier.update(*args, **kwargs)
        self.lock.release()

        return result

    def classify(self, *args, **kwargs):
        self.rwlock.reader_acquire()
        result = self.read_classifier.classify(*args, **kwargs)
        self.rwlock.reader_release()

        return result

    def classify_with_info(self, *args, **kwargs):
        self.rwlock.reader_acquire()
        result = self.read_classifier.classify_with_info(*args, **kwargs)
        self.rwlock.reader_release()

        return result

    def switch(self):
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
        self.classifier = None
        super(SimpleClassifier, self).__init__(*args, **kwargs)

    @staticmethod
    def get_features(sample):
        words = nltk.word_tokenize(sample.text)
        words = set(words)
        feature_set = {}
        for word in words:
            feature_set[word] = True
        return feature_set

    def train(self, samples):
        train_set = []
        for sample in samples:
            if not isinstance(sample, Sample):
                continue
            train_set.append((self.get_features(sample), sample.label))
        self.classifier = nltk.classify.DecisionTreeClassifier.train(
            train_set)

    def classify(self, sample):
        if self.classifier is None:
            return None
        return self.classifier.classify(self.get_features(sample))

    def classify_with_info(self, sample):
        if self.classifier is None:
            return None
        label = self.classifier.classify(self.get_features(sample))
        return {'label': label}
