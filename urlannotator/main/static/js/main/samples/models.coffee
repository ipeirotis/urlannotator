class crud.model.Sample extends crud.model.Model
    urlRoot: '/api/v1/job/'+job_id+'/sample/'

class crud.collection.Samples extends crud.collection.Collection
    model: crud.model.Sample
    urlRoot: '/api/v1/job/'+job_id+'/sample/'

    fetch: () ->
        crud.collection.PaginatedCollection.prototype.fetch.call(this, success: =>
            $('.pop').popover());


class crud.view.SampleTableRow extends crud.view.TableRow
    template: crud.template('js/main/samples/samples-row.ejs')


class crud.view.SampleTable extends crud.view.Table
    itemViewClass: crud.view.SampleTableRow
    template: crud.template('js/main/table.ejs')
