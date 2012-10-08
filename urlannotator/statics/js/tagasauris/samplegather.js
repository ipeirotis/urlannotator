(function(){

    window.getTemplate = function(name){
        var rawTemplate = $("#" + name).html();
        rawTemplate = rawTemplate.replace(/&lt;/g, '<');
        rawTemplate = rawTemplate.replace(/&gt;/g, '>');
        return _.template(rawTemplate);
    };

    window.Sample = Backbone.Model.extend({

        added: null,

        clear: function () {
            Samples.remove(this);
            $(this.view.el).remove();
        },

        update: function () {
            this.view.render();
        }

    });

    window.SampleList = Backbone.Collection.extend({

        model: Sample,

        getAdded: function () {
            return this.map(function (sample) {
                if (sample.added) {
                    return sample.attributes.url;
                }
            });
        }

    });

    window.Samples = new SampleList();

    window.SampleView = Backbone.View.extend({

        tagName: "li",

        className: "sample",

        template: getTemplate("sample"),

        events: {
            "click .sample-remove": "clear"
        },

        initialize: function() {
            this.model.view = this;
        },

        render: function() {
            $(this.el).html(this.template(this.model));
            return this;
        },

        clear: function() {
            this.model.clear();
        }

    });

    window.SampleGather = Backbone.View.extend({

        minSamples: 5,

        // It is set on Tagasauris side
        workerId: null,

        gathered: 0,

        el: $("#form-template"),

        template: getTemplate("samplegather"),

        templateValidatedSample: _.template(
            '<div class="open-question"><input type="text" name="new-sample"'+
            ' value="<%= url %>"></div>'),

        events: {
            "click .add-new-sample": "addNewSample",
            "keypress .new-sample": "checkAddNewSample"
        },

        initialize: function (data) {
            _.bindAll(this);
            Samples.bind("add", this.renderPartial, this);
            Samples.bind("remove", this.renderPartial, this);

            data = $.parseJSON(data);
            this.token = data.token;
            this.jobId = data.job_id;
            this.coreUrl = data.core_url;
            if (data.minSamples !== undefined) {
                this.minSamples = data.min_samples;
            }

            this.render();
        },

        render: function () {
            this.el.html(this.template());
            this.renderPartial();
        },

        renderPartial: function () {
            if (this.gathered >= this.minSamples) {
                this.$('.add-new-sample').attr('disabled', 'disabled');
            } else {
                this.$('.add-new-sample').removeAttr("disabled");
            }
        },

        checkAddNewSample: function (e) {
            if (e.keyCode == 13) {
                e.preventDefault();
                this.addNewSample();
            }
        },

        addNewSample: function () {
            if (this.gathered < this.minSamples) {
                var url = this.$(".new-sample").val();

                sample = new Sample({id:url, url: url});

                var view = new SampleView({model: sample}).render().el;
                this.$(".samples").append(view);
                Samples.add(sample);

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

                        if (that.gathered >= that.minSamples || data.all === true) {
                            that.clearValidatedSamples();
                            that.prepareValidatedSamples();
                            that.sendValidatedSamples();
                        }
                    },
                    "json"
                );
            }
        },

        clearValidatedSamples: function () {
            this.$(".validated-urls").html("");
        },

        prepareValidatedSamples: function () {
            var urls = Samples.getAdded();
            for (var i = urls.length - 1; i >= 0; i--) {
                if (urls[i] !== undefined) {
                    this.$(".validated-urls").append(
                        this.templateValidatedSample({url: urls[i]})
                    );
                }
            }
        },

        sendValidatedSamples: function () {
            this.$(".form-vertical").submit();
        }

    });

    // ExternalApp - alias for SampleGather
    window.ExternalApp = SampleGather;

}());
