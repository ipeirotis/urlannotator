import nltk

from urlannotator.main.models import Sample


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

    def __init__(self, *args, **kwargs):
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
