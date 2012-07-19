import datetime

from urlannotator.main.models import TemporarySample
from urlannotator.main.tasks import (web_content_extraction,
    web_screenshot_extraction, create_sample, create_classify_sample)

from celery import group


class SampleFactory(object):
    """
    Gets:
        Job, worker & url.
    Result:
        None
    """

    def new_sample(self, job_id, worker_id, url='', text=None, label=None,
            *args, **kwargs):
        """
        Produce new sample and starts tasks for screen and text extraction.
        Label argument is passed only when we create GoldenSample.
        """

        # Injecting administrator classification request (no web extraction
        # needed)
        if text is not None:
            return create_classify_sample.delay(job_id, worker_id, url, label,
                *args, **kwargs)

        # Ordinary classification or golden sample.
        else:
            temp_sample = TemporarySample()
            temp_sample.save()

            # Groups screensot and content extraction. On both success proceeds
            # to sample creation. Used Celery Chords.
            return (group([
                web_screenshot_extraction.s(temp_sample.id, url=url),
                web_content_extraction.s(temp_sample.id, url=url)])
                |
                create_sample.s(temp_sample.id, job_id, worker_id, url, label,
                    *args, **kwargs)
            ).apply_async(
                expires=datetime.datetime.now() + datetime.timedelta(days=1)
            )
