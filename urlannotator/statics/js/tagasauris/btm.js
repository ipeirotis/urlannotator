(function(){

    window.SampleView = BaseSampleView.extend({

        template: getTemplate("btm_sample")

    });

    window.BeatTheMachine = BaseExternalApp.extend({

        template: getTemplate("btm"),

        extendedRender: function () {
            var that = this;
            $.get(
                that.coreUrl + '/api/v1/btm/data/tagasauris/' + that.jobId + '/',
                { worker_id: that.workerId },
                function (data) {
                    that.additional_data = data;
                    that.el.html(that.template(data));
                    $(".instructions").append(
                        $(".additional-instruction", that.el).html());

                    if (data.gathered_points !== undefined) {
                        $(".instructions").prepend(
                            $(".additional-notification", that.el).html());
                    }

                    that.removeDuplicateTagasaurisBinding();

                    that.renderPartial();
                    that.pollPoints();
                },
                "json"
            );
        },

        pollPoints: function () {
            var that = this;

            setTimeout(function(){
                $.get(
                    that.coreUrl + '/api/v1/btm/data/tagasauris/' + that.jobId + '/',
                    { worker_id: that.workerId },
                    function (data) {
                        $(".points", $(".instructions")).html(data.gathered_points);
                        $(".pending", $(".instructions")).html(data.pending_verification);
                        that.pollPoints();
                    },
                    "json"
                );
            }, 10000);
        },

        addNewSample: function () {
            if (this.gathered < this.minSamples) {
                var url = this.$(".new-sample").val();

                sample = new Sample({id:url, url: url});

                this.samples.add(sample);

                $(".spinner").show();

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
                            that.$(".sample-error").html("Rejecting url: " +
                                url + ", reason: " + data.result);
                            $(".spinner").hide();
                        }
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
                            sample.max_points = data.max_points;
                            sample.min_points = data.min_points;
                            sample.btm_status = data.btm_status;
                            sample.label_probability = data.label_probability;
                            sample.added = true;
                            that.gathered++;

                            var view = new SampleView({model: sample}
                                ).render().el;
                            that.$(".samples").append(view);

                            that.updatePoints();
                            that.renderPartial();

                            if (that.gathered >= that.minSamples) {
                                that.finishHIT();
                            }

                            $(".spinner").hide();
                        } else {
                            that.pollStatus(sample, status_url, request_id);
                        }
                    },
                "json"
                );
            }, 2000);
        },

        getPoints: function () {
            var points = 0;
            this.samples.each(function (sample) {
                if (sample.points !== undefined) {
                    points += sample.points;
                }
            });
            return points;
        },

        getMaxPoints: function () {
            var points = 0;
            this.samples.each(function (sample) {
                if (sample.points !== undefined) {
                    points += sample.max_points;
                }
            });
            return points;
        },

        updatePoints: function () {
            var points = this.getMaxPoints();
            this.$(".sample-points").html(points);
        }

    });

    // ExternalApp - alias for BeatTheMachine
    window.ExternalApp = BeatTheMachine;

}());
