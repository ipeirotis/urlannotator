# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Classifier'
        db.create_table('classification_classifier', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Job'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('parameters', self.gf('tenclouds.django.jsonfield.fields.JSONField')({}, blank=True)),
        ))
        db.send_create_signal('classification', ['Classifier'])

        # Adding model 'Statistics'
        db.create_table('classification_statistics', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('classification', ['Statistics'])


    def backwards(self, orm):
        # Deleting model 'Classifier'
        db.delete_table('classification_classifier')

        # Deleting model 'Statistics'
        db.delete_table('classification_statistics')


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
        'classification.classifier': {
            'Meta': {'object_name': 'Classifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']"}),
            'parameters': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'classification.statistics': {
            'Meta': {'object_name': 'Statistics'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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
        }
    }

    complete_apps = ['classification']