import datetime
import json

from django.utils.timezone import now

from urlannotator.main.models import (SpentStatistics, ProgressStatistics,
    URLStatistics, LinksStatistics)
from urlannotator.classification.models import ClassifierPerformance


def format_date_val(val):
    """
        Formats a date statistics value into a Date.UTC(y,m,j,H,i,s) format.
    """
    arg_string = val['date'].strftime('%Y,%m-1,%d,%H,%M,%S')
    return '[Date.UTC(%s),%d]' % (arg_string, val['delta'])


def extract_stat(cls, stats):
    """
        Returns a string representing a list of statistics samples formatted
        for use in Highcharts. The closest, earliest value is always used.
    """
    stats = list(stats)
    stats_count = len(stats)
    now_time = now()
    idx = 1
    interval = datetime.timedelta(hours=1)
    actual_time = datetime.datetime(
        year=stats[0].date.year,
        month=stats[0].date.month,
        day=stats[0].date.day,
        hour=stats[0].date.hour,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=stats[0].date.tzinfo,
    )
    list_stats = [{'date': actual_time, 'delta': stats[0].value}]
    actual_time += interval
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
    stats = ProgressStatistics.objects.filter(job=job).order_by('date')
    context['progress_stats'] = extract_stat(ProgressStatistics, stats)


def extract_spent_stats(job, context):
    '''
        Extracts job's money spent statistics as difference per hour.
    '''
    stats = SpentStatistics.objects.filter(job=job).order_by('date')
    context['spent_stats'] = extract_stat(SpentStatistics, stats)


def extract_url_stats(job, context):
    '''
        Extracts job's url statistics as difference per hour.
    '''
    stats = URLStatistics.objects.filter(job=job).order_by('date')
    context['url_stats'] = extract_stat(URLStatistics, stats)


def extract_workerlinks_stats(worker, context):
    '''
        Extracts job's url statistics as difference per hour.
    '''
    stats = LinksStatistics.objects.filter(worker=worker).order_by('date')
    context['workerlinks_stats'] = extract_stat(LinksStatistics, stats)


def extract_stat_by_val(cls, job, val_fun):
    '''
        Extracts stat using a val_fun to take value from entry.
    '''
    stats = cls.objects.filter(job=job).order_by('date')
    stats = list(stats)
    stats_count = len(stats)
    now_time = now()
    actual_time = datetime.datetime(
        year=stats[0].date.year,
        month=stats[0].date.month,
        day=stats[0].date.day,
        hour=stats[0].date.hour,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=stats[0].date.tzinfo,
    )
    idx = 1
    interval = datetime.timedelta(hours=1)
    list_stats = [{'date': actual_time, 'delta': val_fun(stats[0])}]
    actual_time += interval
    actual_value = val_fun(stats[0])

    while actual_time <= now_time:
        # Find next closest sample
        while idx < stats_count:
            if stats[idx].date > actual_time:
                break
            idx += 1

        stat = stats[idx - 1]
        list_stats.append({
            'date': actual_time,
            'delta': val_fun(stat) - actual_value
        })
        actual_value = val_fun(stat)
        actual_time += interval

    stats = ','.join([format_date_val(v) for v in list_stats])
    return stats


def extract_performance_stats(job, context):
    '''
        Extracts job's performance statistics as difference per hour.
    '''
    extract_TPR = lambda x: x.value.get('TPR', 0)
    extract_TNR = lambda x: x.value.get('TNR', 0)
    extract_AUC = lambda x: x.value.get('AUC', 0)
    context['performance_TPR'] = extract_stat_by_val(
        ClassifierPerformance,
        job,
        extract_TPR
    )
    context['performance_TNR'] = extract_stat_by_val(
        ClassifierPerformance,
        job,
        extract_TNR
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
    div = (yesCount + noCount) or 1
    return ('TPR', round(yesCount / div, 4))


def TrueNegativeMetric(classifier, job, analyze):
    '''
        Calculates probability of saying No if the label is No in real.
    '''
    matrix = analyze['modelDescription']['confusionMatrix']
    yesCount = matrix['No']['Yes']
    noCount = matrix['No']['No']
    div = (yesCount + noCount) or 1
    return ('TNR', round(noCount / div, 4))


def AUCMetric(classifier, job, analyze):
    '''
        Calculates 'Area Under the Curve' metric.
    '''
    TPR = TruePositiveMetric(classifier, job, analyze)
    TNR = TrueNegativeMetric(classifier, job, analyze)
    return ('AUC', round((TPR[1] + TNR[1]) / 2.0, 4))

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
