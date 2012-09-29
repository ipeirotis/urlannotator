(function(){

    window.Sample = Backbone.Model.extend({

        clear: function () {
            Samples.remove(this);
            $(this.view.el).remove();
        }

    });

    window.SampleList = Backbone.Collection.extend({

        model: Sample

    });

    window.Samples = new SampleList();

    window.SampleView = Backbone.View.extend({

        tagName: "li",

        className: "sample",

        template: _.template(
            '<span><%= url %></span>'+
            ' <a href="#" class="sample-remove">remove</a>'),

        events: {
            "click .sample-remove": "clear"
        },

        initialize: function() {
            this.model.view = this;
        },

        render: function() {
            $(this.el).html(this.template(this.model.toJSON()));
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
                {urls: urls},
                function (data) {
                    console.log(data);
                }
            );
        }

    });

    // ExternalApp - alias for SampleGather
    window.ExternalApp = SampleGather;

}());
