(function(){

    window.SampleView = BaseSampleView.extend({

        template: getTemplate("btm_sample")

    });

    window.BeatTheMachine = BaseExternalApp.extend({

        template: getTemplate("btm"),

        addNewSample: function () {
            if (this.gathered < this.minSamples) {
                var url = this.$(".new-sample").val();
                var expectedLabel = this.$(".expected-label").val();

                sample = new Sample({id:url, url: url, label: expectedLabel});

                var view = new SampleView({model: sample}).render().el;
                this.$(".samples").append(view);
                Samples.add(sample);

                var that = this;
                $.post(
                    this.coreUrl + '/api/v1/btm/add/tagasauris/' +
                        this.jobId + '/',
                    JSON.stringify({url: url, label: expectedLabel,
                        worker_id: this.workerId}),
                    function (data) {
                        if (data.request_id !== undefined) {
                            that.pollStatus(sample, data.status_url,
                                data.request_id);
                        } else {
                            sample.status = data.error;
                        }

                        sample.update();
                    },
                    "json"
                );
            }
        },

        pollStatus: function (sample, status_url, request_id) {
            var that = this;

            setTimeout(function(){
                $.get(
                    that.coreUrl + status_url,
                    {request_id: request_id},
                    function (data) {
                        if (data.labels_matched !== undefined) {
                            if (data.labels_matched) {
                                sample.matched = true;
                            } else {
                                sample.matched = false;
                            }
                            that.gathered++;
                        } else {
                            pollStatus(sample, status_url, request_id);
                        }

                        sample.update();

                        if (that.gathered >= that.minSamples) {
                            that.finishHIT();
                        }
                    }
                );
            }, 2000);
        }

    });

    // ExternalApp - alias for BeatTheMachine
    window.ExternalApp = BeatTheMachine;

}());
