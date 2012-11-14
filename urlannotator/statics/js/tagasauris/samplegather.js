(function(){

    window.SampleView = BaseSampleView.extend({

        template: getTemplate("sample")

    });

    window.SampleGather = BaseExternalApp.extend({

        template: getTemplate("samplegather"),

        expandReason: function (reason) {
            var description = "";
            if (reason == "duplicate") {
                description = "Given url already exists in our database. Please try another url.";
            } else if (reason == "domain duplicate") {
                description = "Given url domain already exists in our database. Please try another url.";
            } else if (reason == "malformed url") {
                description = "Given url is not valid. Please try another url.";
            } else {
                description = reason;
            }
            return description;
        },

        addNewSample: function () {
            if (this.gathered < this.minSamples) {
                var url = this.$(".new-sample").val();
                var that = this;
                $.post(
                    this.coreUrl + '/api/v1/sample/add/tagasauris/' +
                        this.jobId + '/',
                    JSON.stringify({url: url, worker_id: this.workerId}),
                    function (data) {
                        if (data.result === 'added') {
                            var sample = new Sample({id:url, url: url});
                            sample.added = true;

                            that.samples.add(sample);

                            var view = new SampleView({model: sample}).render().el;
                            that.$(".samples").append(view);

                            that.gathered++;
                            that.$(".sample-error").html("");
                        } else {
                            that.$(".sample-error").html("Rejecting url: " +
                                url + ", Reason: " +
                                that.expandReason(data.result));
                        }

                        that.renderPartial();

                        if (that.gathered >= that.minSamples ||
                                data.all === true) {
                            that.finishHIT();
                        }
                    },
                    "json"
                );
            }
        }

    });

    // ExternalApp - alias for SampleGather
    window.ExternalApp = SampleGather;

}());
