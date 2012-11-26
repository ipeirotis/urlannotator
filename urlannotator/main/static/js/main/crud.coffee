$ ->

    _.extend crud.settings, {'static_url': '/statics'}

    workers = new crud.collection.Workers

    workers.fetchMeta (meta) ->

        workersTable = new crud.view.WorkerTable
            el: $('#workers-table')
            meta: meta
            collection: workers

        workersTable.render()
        workers.fetch()