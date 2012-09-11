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

        template: _.template('\
            <label class="control-label" for="input_1">Good url</label>\
            <div class="controls">\
                <input id="input_1" class="input input-xlarge required"\
                    type="text" name="1" >\
            </div>\
        '),

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

        gatherFormTemplate: _.template('\
        <form class="form-vertical" data-validate="ketchup"\
        <fieldset>\
            <div class="question-group">\
            <h2>Enter url samples</h2>\
            <div id="questions" class="control-group open-question">\
            </div>\
        </fieldset>\
        <input type="submit" value="Submit">\
        </form>\
        '),

        events: {
            "keypress #new-todo": "sendOnEnter"
        },

        start_job: function (external_token) {
            this.external_token = external_token;
            this.render();
        },

        initialize: function() {
        },

        render: function() {
            $("#form-template").html(this.gatherFormTemplate());
            $("#questions")
        },

        sendOnEnter: function(e) {
            if (e.code != 13) return;
            Inputs.create({
                content: this.input.getProperty("value"),
                done:        false
            });
            this.input.setProperty("value", "");
        }

    });

    // ExternalApp - alias for SampleGather
    window.ExternalApp = SampleGather;

}());
