(function(){

    window.Input = Backbone.Model.extend({

        toggle: function () {
            this.save({done: !this.get("done")});
        },

        // Remove this Input from *localStorage*, deleting its view.
        clear: function () {
            this.destroy();
            $(this.view.el).dispose();
        }

    });

    // Input List
    window.InputList = Backbone.Collection.extend({

        model: Input

    });

    window.Inputs = new InputList();

    window.InputView = Backbone.View.extend({

        tagName: "div",

        className: "sampleInput",

        // template: _.template(TemplateGetter.get("../../ejs/tagasauris/inputsample.ejs")),

        events: {
            "click .todo-check"            : "toggleDone",
            "dblclick .todo-content" : "edit",
            "click .todo-destroy"        : "clear",
            "keypress .todo-input"     : "updateOnEnter"
        },

        initialize: function() {
            _.bindAll(this, 'render', 'close');
            this.model.bind('change', this.render);
            this.model.view = this;
        },

        render: function() {
            $(this.el).set('html', this.template(this.model.toJSON()));
            $(this.el).setProperty("id", "todo-"+this.model.id);
            this.setContent();
            sortableTodos.addItems(this.el);
            return this;
        },

        setContent: function() {
            var content = this.model.get('content');
            this.$('.todo-content').set("html", content);
            this.$('.todo-input').setProperty("value", content);

            if (this.model.get('done')) {
                this.$(".todo-check").setProperty("checked", "checked");
                $(this.el).addClass("done");
            } else {
                this.$(".todo-check").removeProperty("checked");
                $(this.el).removeClass("done");
            }

            this.input = this.$(".todo-input");
            this.input.addEvent('blur', this.close);
        },

        toggleDone: function() {
            this.model.toggle();
        },

        edit: function() {
            $(this.el).addClass("editing");
            //this.input.fireEvent("focus");
            this.input.focus();
        },

        close: function() {
            this.model.save({content: this.input.getProperty("value")});
            $(this.el).removeClass("editing");
        },

        updateOnEnter: function(e) {
            if (e.code == 13) this.close();
        },

        clear: function() {
            this.model.clear();
        }

    });

    window.SampleGather = Backbone.View.extend({

        el: $("samplegatherapp"),

        template: null,

        events: {
            "keypress #new-todo": "sendOnEnter"
        },

        start_job: function (data) {
            data = $.parseJSON(data);
            this.token = data.token;
            this.core_url = data.core_url;

            this.template = _.template($("#samplegather").html()),
            this.render();
        },

        initialize: function() {
        },

        render: function() {
            $("#form-template").html(this.template());
            // $("#questions")
        },

        sendOnEnter: function(e) {
            if (e.code != 13) return;
            Inputs.create({
                content: this.input.getProperty("value"),
                done: false
            });
            this.input.setProperty("value", "");
        }

    });

    // ExternalApp - alias for SampleGather
    window.ExternalApp = SampleGather;

}());
