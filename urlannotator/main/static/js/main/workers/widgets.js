crud.view.IntegerWidget = crud.view.FullTextSearchItem.extend({

    tagName: 'li',

    template: crud.template('js/main/workers/integer_widget.ejs'),

    search: function () {
        this.clearSearchTrigger();

        var val = parseInt(this.$('input').val());

        if (this._lastSearchKey || this._lastSearchKey == NaN) {
            this.collection.removeFilter(this._lastSearchKey);
            delete this._lastSearchKey;
        }

        if (!isNaN(val)) {
            this._lastSearchKey = this.options.filter.key + ':' + val;
            this.collection.addFilter(this._lastSearchKey);
        }
        this.collection.fetch();
    },

    render: function () {
        var value = this.$('input').val() || '';
        $(this.el).html(this.template.render({key: this.options.filter.key, value: value, name: this.options.filter.name}));
        return this;
    }
});

crud.view.standardFilterWidgets['integer'] = crud.view.IntegerWidget
