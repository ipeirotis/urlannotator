$ ->

    _.extend crud.settings, {'static_url': '/statics'}

    samples = new crud.collection.Samples

    samples.fetchMeta (meta) ->

        samplesTable = new crud.view.SampleTable
            el: $('#samples-table')
            meta: meta
            collection: samples

        samplesTable.render()
        samples.fetch()