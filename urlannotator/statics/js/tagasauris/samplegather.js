(function(){

    window.SampleView = BaseSampleView.extend({

        template: getTemplate("sample")

    });

    window.SampleGather = BaseExternalApp.extend({

        template: getTemplate("samplegather"),

        addNewSample: function () {
            if (this.gathered < this.minSamples) {
                var url = this.$(".new-sample").val();

                sample = new Sample({id:url, url: url});

                var view = new SampleView({model: sample}).render().el;
                this.$(".samples").append(view);
                this.samples.add(sample);

                var that = this;
                $.post(
                    this.coreUrl + '/api/v1/sample/add/tagasauris/' +
                        this.jobId + '/',
                    JSON.stringify({url: url, worker_id: this.workerId}),
                    function (data) {
                        if (data.result === 'added') {
                            sample.added = true;
                            that.gathered++;
                        } else {
                            sample.added = false;
                            sample.reason = data.result;
                        }
                        sample.update();
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
