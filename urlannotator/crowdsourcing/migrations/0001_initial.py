# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'WorkerQualityVote'
        db.create_table('crowdsourcing_workerqualityvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('worker', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Worker'])),
            ('sample', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Sample'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('added_on', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('crowdsourcing', ['WorkerQualityVote'])

        # Adding model 'GoldSample'
        db.create_table('crowdsourcing_goldsample', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sample', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Sample'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('crowdsourcing', ['GoldSample'])

        # Adding model 'BeatTheMachineSamples'
        db.create_table('crowdsourcing_beatthemachinesamples', (
            ('sample_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['main.Sample'], unique=True, primary_key=True)),
            ('expected_output', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('classifier_output', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('error_ratio', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=7, decimal_places=5)),
        ))
        db.send_create_signal('crowdsourcing', ['BeatTheMachineSamples'])


    def backwards(self, orm):
        # Deleting model 'WorkerQualityVote'
        db.delete_table('crowdsourcing_workerqualityvote')

        # Deleting model 'GoldSample'
        db.delete_table('crowdsourcing_goldsample')

        # Deleting model 'BeatTheMachineSamples'
        db.delete_table('crowdsourcing_beatthemachinesamples')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'crowdsourcing.beatthemachinesamples': {
            'Meta': {'object_name': 'BeatTheMachineSamples', '_ormbases': ['main.Sample']},
            'classifier_output': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'error_ratio': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '7', 'decimal_places': '5'}),
            'expected_output': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'sample_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['main.Sample']", 'unique': 'True', 'primary_key': 'True'})
        },
        'crowdsourcing.goldsample': {
            'Meta': {'object_name': 'GoldSample'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'sample': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Sample']"})
        },
        'crowdsourcing.workerqualityvote': {
            'Meta': {'object_name': 'WorkerQualityVote'},
            'added_on': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'sample': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Sample']"}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Worker']"})
        },
        'main.account': {
            'Meta': {'object_name': 'Account'},
            'activation_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'alerts': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email_registered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'full_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'odesk_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'odesk_uid': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'main.job': {
            'Meta': {'object_name': 'Job'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': "orm['main.Account']"}),
            'budget': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '2'}),
            'data_source': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'hourly_rate': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'no_of_urls': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'progress': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'same_domain_allowed': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'main.sample': {
            'Meta': {'object_name': 'Sample'},
            'added_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Worker']"}),
            'added_on': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']"}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'screenshot': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'main.worker': {
            'Meta': {'object_name': 'Worker'},
            'estimated_quality': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '7', 'decimal_places': '5'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        }
    }

    complete_apps = ['crowdsourcing']