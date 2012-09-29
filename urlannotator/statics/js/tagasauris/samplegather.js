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
            ' <% if (duplicate) { %><span class="duplicate">DUPLICATE</span><% } %>'+
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

        el: $("#form-template"),

        template: _.template($("#samplegather").html()),

        events: {
            "click .add-new-sample": "addNewSample",
            "click .submit-samples": "sendSamples"
        },

        initialize: function (data) {
            data = $.parseJSON(data);
            this.token = data.token;
            this.job_id = data.job_id;
            this.core_url = data.core_url;

            this.render();
        },

        render: function () {
            this.el.html(this.template());
        },

        addNewSample: function () {
            var url = this.$(".new-sample").val();

            sample = new Sample({id:url, url: url});

            var view = new SampleView({model: sample}).render().el;
            this.$(".samples").append(view);
            Samples.add(sample);
        },

        sendSamples: function () {
            var urls = $.map(Samples.toArray(), function(sample) {
                return sample.get('url');
            });
            $.post(
                this.core_url + '/api/v1/sample/verify/' + this.job_id + '/',
                JSON.stringify({urls: urls}),
                function (data) {
                    if (data.duplicate_urls.length === 0) {

                    } else {
                        Samples.setDuplicates(data.duplicate_urls);
                    }
                },
                "json"
            );
        }

    });

    // ExternalApp - alias for SampleGather
    window.ExternalApp = SampleGather;

}());
