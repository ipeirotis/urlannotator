PIPELINE_JS = {
    'core': {
        'source_filenames': (
            'js/jquery-1.7.2.js',
            'js/ejs.min.js',
            'js/underscore.js',
            'js/json2.js',
            'js/backbone.js',
            'js/bootstrap.js',
            'js/bootstrap-tooltip.js',
        ),
        'output_filename': 'js/core.min.js',
    },
    'crud': {
        'source_filenames': (
            'tenclouds/django/crud/statics/js/init.js',
            'tenclouds/django/crud/statics/js/events.js',
            'tenclouds/django/crud/statics/js/models.js',
            'tenclouds/django/crud/statics/js/views.js',
            'tenclouds/django/crud/statics/js/widgets.js',
        ),
        'output_filename': 'crud.js',
    },
    'less': {
        'source_filenames': (
            'js/less-1.3.0.js',
        ),
        'output_filename': 'js/less.min.js',
    }
}
