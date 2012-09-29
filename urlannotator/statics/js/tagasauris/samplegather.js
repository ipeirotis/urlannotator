(function(){

    window.Sample = Backbone.Model.extend({

        duplicate: false,

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

        setDuplicates: function (duplicates) {
            this.map(function (sample) {
                sample.duplicate = false;
            });
            for (var i = duplicates.length - 1; i >= 0; i--) {
                var sample = Samples.get(duplicates[i]);
                sample.duplicate = true;
                sample.update();
            }
        }

    });

    window.Samples = new SampleList();

    window.SampleView = Backbone.View.extend({

        tagName: "li",

        className: "sample",

        template: _.template(
            '<span><%= attributes.url %></span>'+
            ' <% if (duplicate) { %>'+
            ' <span class="duplicate">DUPLICATE</span><% } %>'+
            ' <a href="#" class="sample-remove">remove</a>'),

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

        minSamples: 1,

        maxSamples: 5,

        el: $("#form-template"),

        template: _.template($("#samplegather").html()),

        templateValidatedSample: _.template(
            '<input class="open-question" type="text" name="new-sample"'+
            ' value="<%= url %>">'),

        events: {
            "click .add-new-sample": "addNewSample",
            "click .submit-samples": "sendSamples",
            "keypress .new-sample": "checkAddNewSample"
        },

        initialize: function (data) {
            _.bindAll(this);
            Samples.bind("add", this.renderPartial, this);
            Samples.bind("remove", this.renderPartial, this);

            data = $.parseJSON(data);
            this.token = data.token;
            this.job_id = data.job_id;
            this.core_url = data.core_url;

            this.render();
        },

        render: function () {
            this.el.html(this.template());
            this.renderPartial();
        },

        renderPartial: function () {
            if (Samples.length >= this.maxSamples) {
                this.$('.add-new-sample').attr('disabled', 'disabled');
            } else {
                this.$('.add-new-sample').removeAttr("disabled");
            }

            if (Samples.length < this.minSamples) {
                this.$('.submit-samples').attr('disabled', 'disabled');
            } else {
                this.$('.submit-samples').removeAttr("disabled");
            }
        },

        checkAddNewSample: function (e) {
            if (e.keyCode == 13) {
                e.preventDefault();
                this.addNewSample();
            }
        },

        addNewSample: function () {
            if (Samples.length < this.maxSamples) {
                var url = this.$(".new-sample").val();

                sample = new Sample({id:url, url: url});

                var view = new SampleView({model: sample}).render().el;
                this.$(".samples").append(view);
                Samples.add(sample);
            }
        },

        clearValidatedSamples: function () {
            this.$(".validated-urls").html("");
        },

        prepareValidatedSamples: function (urls) {
            for (var i = urls.length - 1; i >= 0; i--) {
                this.$(".validated-urls").append(
                    this.templateValidatedSample({url: urls[i]})
                );
            }
        },

        sendValidatedSamples: function () {
            this.$(".form-vertical").submit();
        },

        sendSamples: function () {
            if (Samples.length >= this.minSamples) {
                var urls = $.map(Samples.toArray(), function(sample) {
                    return sample.get('url');
                });

                var that = this;

                $.post(
                    this.core_url + '/api/v1/sample/verify/' + this.job_id +
                        '/',
                    JSON.stringify({urls: urls}),
                    function (data) {
                        if (data.duplicate_urls.length === 0) {
                            that.clearValidatedSamples();
                            that.prepareValidatedSamples(urls);
                            that.sendValidatedSamples();
                        } else {
                            Samples.setDuplicates(data.duplicate_urls);
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
