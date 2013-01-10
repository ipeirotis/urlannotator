$ ->

    _.extend crud.settings, {'static_url': '/statics'}

    workers = new crud.collection.Workers

    workers.fetchMeta (meta) ->
        filteredWorkers = new crud.collection.Workers()

        filteredWorkers.fetchMeta (workersMeta) ->

            workersTable = new crud.view.WorkerTable
                el: $('#workers-table')
                meta: workersMeta
                collection: filteredWorkers

            fV = new crud.view.FilterList(
              collection: filteredWorkers
              filterGroups: workersMeta.filterGroups
            )
            $(".sidebar-nav").append fV.render().el

            # fetch data
            filteredWorkers.fetch()
