(function(){

    window.SampleView = BaseSampleView.extend({

        template: getTemplate("btm_sample")

    });

    window.BeatTheMachine = BaseExternalApp.extend({

        template: getTemplate("btm"),

        addNewSample: function () {
            if (this.gathered < this.minSamples) {
                var url = this.$(".new-sample").val();

                sample = new Sample({id:url, url: url});

                var view = new SampleView({model: sample}).render().el;
                this.$(".samples").append(view);
                Samples.add(sample);

                var that = this;
                $.post(
                    this.coreUrl + '/api/v1/btm/add/tagasauris/' +
                        this.jobId + '/',
                    JSON.stringify({url: url, worker_id: this.workerId}),
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
                        if (data.points !== undefined) {
                            sample.points = data.points;
                            sample.description = data.description;
                            that.gathered++;

                            sample.update();
                            that.updatePoints();

                            if (that.gathered >= that.minSamples) {
                                that.finishHIT();
                            }
                        } else {
                            pollStatus(sample, status_url, request_id);
                        }
                    }
                );
            }, 2000);
        },

        getPoints: function () {
            var points = 0;
            this.samples.each(function (sample) {
                points += sample.points;
            });
            return points;
        },

        updatePoints: function () {
            var points = this.getPoints();
            this.$(".sample-points").html(points);
        }

    });

    // ExternalApp - alias for BeatTheMachine
    window.ExternalApp = BeatTheMachine;

}());
