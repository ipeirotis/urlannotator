Useful tips when developing
===========================


Fast checking who listenes on given event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To do this just run:

  $ ./manage.py flow_analysis

Should result in output like this:

::

    ^EventTrainingSetCompleted$
        classification.event_handlers.train_on_set

    ^EventNewRawSample$
        main.event_handlers.EventRawSampleManager

    ^EventNewSample$
        classification.event_handlers.update_classified_sample
        crowdsourcing.event_handlers.SamplesValidationManager

    ^TestEvent$
        flow_control.event_handlers.test_task

    ^EventClassifierTrained$
        classification.event_handlers.update_classifier_stats

    ^EventNewGoldSample$
        main.event_handlers.GoldSamplesMonitor

    ^EventNewJobInitialization$
        crowdsourcing.event_handlers.ExternalJobsManager
        main.event_handlers.JobFactoryManager

    ^EventNewClassifySample$
        classification.event_handlers.classify

    ^EventSamplesValidated$
        classification.event_handlers.ClassifierTrainingManager


