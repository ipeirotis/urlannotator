# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Account'
        db.create_table('main_account', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('activation_key', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('email_registered', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('odesk_key', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('odesk_uid', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('full_name', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('alerts', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('main', ['Account'])

        # Adding model 'Job'
        db.create_table('main_job', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(related_name='project', to=orm['main.Account'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('progress', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('no_of_urls', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('data_source', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('project_type', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('same_domain_allowed', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('hourly_rate', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=2)),
            ('budget', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=2)),
        ))
        db.send_create_signal('main', ['Job'])

        # Adding model 'Worker'
        db.create_table('main_worker', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('external_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('estimated_quality', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=7, decimal_places=5)),
        ))
        db.send_create_signal('main', ['Worker'])

        # Adding model 'Sample'
        db.create_table('main_sample', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Job'])),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('screenshot', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('added_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Worker'])),
            ('added_on', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('main', ['Sample'])

        # Adding model 'TemporarySample'
        db.create_table('main_temporarysample', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('screenshot', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('main', ['TemporarySample'])


    def backwards(self, orm):
        # Deleting model 'Account'
        db.delete_table('main_account')

        # Deleting model 'Job'
        db.delete_table('main_job')

        # Deleting model 'Worker'
        db.delete_table('main_worker')

        # Deleting model 'Sample'
        db.delete_table('main_sample')

        # Deleting model 'TemporarySample'
        db.delete_table('main_temporarysample')


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
        'main.temporarysample': {
            'Meta': {'object_name': 'TemporarySample'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'screenshot': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'text': ('django.db.models.fields.TextField', [], {})
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

    complete_apps = ['main']