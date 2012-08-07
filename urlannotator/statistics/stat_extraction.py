import datetime
import json

from django.utils.timezone import now

from urlannotator.main.models import (SpentStatistics, ProgressStatistics,
    URLStatistics)
from urlannotator.classification.models import ClassifierPerformance


def format_date_val(val):
    """
        Formats a date statistics value into a Date.UTC(y,m,j,H,i,s) format.
    """
    arg_string = val['date'].strftime('%Y,%m-1,%d,%H,%M,%S')
    return '[Date.UTC(%s),%d]' % (arg_string, val['delta'])


def extract_stat(cls, job):
    """
        Returns a string representing a list of statistics samples formatted
        for use in Highcharts. The closest, earliest value is always used.
    """
    stats = cls.objects.filter(job=job).order_by('date')
    stats_count = stats.count()
    list_stats = [{'date': stats[0].date, 'delta': stats[0].value}]
    now_time = now()
    idx = 1
    interval = datetime.timedelta(hours=1)
    actual_time = stats[0].date + interval
    actual_value = stats[0].value

    while actual_time <= now_time:
        # Find next closest sample
        while idx < stats_count:
            if stats[idx].date > actual_time:
                break
            idx += 1

        stat = stats[idx - 1]
        list_stats.append({
            'date': actual_time,
            'delta': stat.value - actual_value
        })
        actual_value = stat.value
        actual_time += interval

    stats = ','.join([format_date_val(v) for v in list_stats])
    return stats


def extract_progress_stats(job, context):
    '''
        Extracts job's progress statistics as difference per hour.
    '''
    context['progress_stats'] = extract_stat(ProgressStatistics, job)


def extract_spent_stats(job, context):
    '''
        Extracts job's money spent statistics as difference per hour.
    '''
    context['spent_stats'] = extract_stat(SpentStatistics, job)


def extract_url_stats(job, context):
    '''
        Extracts job's url statistics as difference per hour.
    '''
    context['url_stats'] = extract_stat(URLStatistics, job)


def extract_stat_by_val(cls, job, val_fun):
    '''
        Extracts stat using a val_fun to take value from entry.
    '''
    stats = cls.objects.filter(job=job).order_by('date')
    list_stats = [{'date': stats[0].date, 'delta': val_fun(stats[0])}]
    actual_value = val_fun(stats[0])

    for stat in stats:
        print stat.value
        list_stats.append({
            'date': stat.date,
            'delta': val_fun(stat) - actual_value
        })
        actual_value = val_fun(stat)

    stats = ','.join([format_date_val(v) for v in list_stats])
    return stats


def extract_performance_stats(job, context):
    '''
        Extracts job's performance statistics as difference per hour.
    '''
    extract_TPM = lambda x: x.value.get('TPM', 0)
    extract_TNM = lambda x: x.value.get('TNM', 0)
    extract_AUC = lambda x: x.value.get('AUC', 0)
    context['performance_TPM'] = extract_stat_by_val(
        ClassifierPerformance,
        job,
        extract_TPM
    )
    context['performance_TNM'] = extract_stat_by_val(
        ClassifierPerformance,
        job,
        extract_TNM
    )
    context['performance_AUC'] = extract_stat_by_val(
        ClassifierPerformance,
        job,
        extract_AUC
    )


def TruePositiveMetric(classifier, job, analyze):
    '''
        Calculates probability of saying True if the label is True in real.
    '''
    matrix = analyze['modelDescription']['confusionMatrix']
    yesCount = matrix['Yes']['Yes']
    noCount = matrix['Yes']['No']
    return ('TPM', round(yesCount / (yesCount + noCount), 4))


def TrueNegativeMetric(classifier, job, analyze):
    '''
        Calculates probability of saying No if the label is No in real.
    '''
    matrix = analyze['modelDescription']['confusionMatrix']
    yesCount = matrix['No']['Yes']
    noCount = matrix['No']['No']
    return ('TNM', round(noCount / (yesCount + noCount), 4))


def AUCMetric(classifier, job, analyze):
    '''
        Calculates 'Area Under the Curve' metric.
    '''
    TPM = TruePositiveMetric(classifier, job, analyze)
    TNM = TrueNegativeMetric(classifier, job, analyze)
    return ('AUC', round((TPM[1] + TNM[1]) / 2.0, 4))

# List of classifier performance metrics to be calculated, stored and displayed
# on the performance chart
CLASSIFIER_PERFORMANCE_METRICS = (
    TruePositiveMetric,
    TrueNegativeMetric,
    AUCMetric,
)


def update_classifier_stats(classifier, job):
    '''
        Updates classifier performance statistics based on given metrics.
    '''
    stats = {}
    analyze = classifier.analyze()
    for metric in CLASSIFIER_PERFORMANCE_METRICS:
        v = metric(classifier, job, analyze)
        stats[v[0]] = v[1]

    ClassifierPerformance.objects.create(
        job=job,
        value=json.dumps(stats)
    )
