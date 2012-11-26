class crud.model.Worker extends crud.model.Model
    urlRoot: '/api/v1/job/'+job_id+'/worker/'

class crud.collection.Workers extends crud.collection.Collection
    model: crud.model.Worker
    urlRoot: '/api/v1/job/'+job_id+'/worker/'

class crud.view.WorkerTableRow extends crud.view.TableRow
    # empty

class crud.view.WorkerTable extends crud.view.Table
    itemViewClass: crud.view.WorkerTableRow