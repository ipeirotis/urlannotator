from urlannotator.main.models import TemporarySample
from urlannotator.main.tasks import (web_content_extraction,
    web_screenshot_extraction, create_sample)

from celery import group


class SampleFactory():
    """
    Gets:
        Job, worker & url.
    Result:
        None
    """

    @classmethod
    def new_sample(cls, job, worker, url):
        """ Produce new sample and starts tasks for screen and text extraction.
        """

        temp_sample = TemporarySample()
        temp_sample.save()

        # Groups screensot and content extraction. On both success proceeds to
        # sample creation. Used Celery Chords.
        (group([
            web_screenshot_extraction.s(temp_sample.id, url=url),
            web_content_extraction.s(temp_sample.id, url=url)])
            |
            create_sample.s(temp_sample.id, job.id, worker.id, url)
        )().apply_async()
