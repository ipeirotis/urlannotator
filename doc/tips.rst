Useful tips when developing
===========================


Fast checking who listenes on given event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To do this just run:

  $ ./manage.py flow_analysis

Should result in output like this:

::

    ^EventSampleContentDone$
        logging.event_handlers.log_sample_text_done

    ^EventTrainingSetCompleted$
        classification.event_handlers.train_on_set
        logging.event_handlers.log_classifier_train_start

    ^EventNewRawSample$
        main.event_handlers.EventRawSampleManager
        logging.event_handlers.log_new_sample_start

    ^EventNewSample$
        classification.event_handlers.update_classified_sample
        logging.event_handlers.log_sample_done

    ^EventProcessVotes$
        classification.event_handlers.ProcessVotesManager

    ^EventNewJobInitializationDone$
        logging.event_handlers.log_new_job_done

    ^TestEvent$
        flow_control.event_handlers.test_task

    ^EventClassifierTrained$
        classification.event_handlers.update_classifier_stats
        logging.event_handlers.log_classifier_trained

    ^EventSamplesVoting$
        classification.event_handlers.SampleVotingManager

    ^EventNewJobInitialization$
        crowdsourcing.event_handlers.ExternalJobsManager
        main.event_handlers.JobFactoryManager
        logging.event_handlers.log_new_job

    ^EventNewGoldSample$
        main.event_handlers.GoldSamplesMonitor
        logging.event_handlers.log_gold_sample_done

    ^EventClassifierCriticalTrainError$
        logging.event_handlers.log_classifier_critical_train_error

    ^EventSampleClassified$
        logging.event_handlers.log_sample_classified

    ^EventClassifierTrainError$
        logging.event_handlers.log_classifier_train_error

    ^EventNewClassifySample$
        classification.event_handlers.classify

    ^EventSampleScreenshotFail$
        logging.event_handlers.log_sample_screenshot_fail

    ^EventSampleScreenshotDone$
        logging.event_handlers.log_sample_screenshot_done
