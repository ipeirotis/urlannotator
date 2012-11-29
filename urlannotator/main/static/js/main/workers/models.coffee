class crud.model.Worker extends crud.model.Model
    urlRoot: '/api/v1/job/'+job_id+'/worker/'

class crud.collection.Workers extends crud.collection.Collection
    model: crud.model.Worker
    urlRoot: '/api/v1/job/'+job_id+'/worker/'

class crud.view.WorkerTableRow extends crud.view.TableRow
    # empty

class crud.view.WorkerTable extends crud.view.Table
    itemViewClass: crud.view.WorkerTableRow
    template: crud.template('js/main/table.ejs')

class crud.model.Sample extends crud.model.Model
    urlRoot: '/api/v1/job/'+job_id+'/sample/'

class crud.collection.Samples extends crud.collection.Collection
    model: crud.model.Sample
    urlRoot: '/api/v1/job/'+job_id+'/sample/'

class crud.view.SampleTableRow extends crud.view.TableRow
    template: crud.template('js/main/samples-row.ejs')

class crud.view.SampleTable extends crud.view.Table
    itemViewClass: crud.view.SampleTableRow
    template: crud.template('js/main/table.ejs')