# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'BTMBonusPayment.job'
        db.add_column('payments_btmbonuspayment', 'job',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Job'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'BTMBonusPayment.job'
        db.delete_column('payments_btmbonuspayment', 'job_id')


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
            'odesk_secret': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'odesk_token': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'odesk_uid': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'worker_entry': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['main.Worker']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'main.job': {
            'Meta': {'object_name': 'Job'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Account']"}),
            'activated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'add_filler_samples': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'btm_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'btm_points_to_cash': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'btm_to_gather': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'budget': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '2'}),
            'classify_urls': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
            'collected_urls': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'data_source': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'gold_samples': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
            'hourly_rate': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initialization_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'no_of_urls': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'progress': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'quality_algorithm': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'remaining_urls': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'same_domain_allowed': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "'test'", 'max_length': '100'}),
            'votes_storage': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'main.worker': {
            'Meta': {'object_name': 'Worker'},
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'worker_type': ('django.db.models.fields.IntegerField', [], {'max_length': '100'})
        },
        'payments.btmbonuspayment': {
            'Meta': {'object_name': 'BTMBonusPayment'},
            'additional_data': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '2'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']", 'null': 'True'}),
            'points_covered': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'sub_status': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Worker']"})
        },
        'payments.jobpaymentsettings': {
            'Meta': {'unique_together': "(['job', 'main'],)", 'object_name': 'JobPaymentSettings'},
            'backend': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'backend_params': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']"}),
            'main': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'split_budget': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'})
        },
        'payments.workerpayment': {
            'Meta': {'object_name': 'WorkerPayment'},
            'additional_data': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '2'}),
            'backend': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'combined_payment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['payments.WorkerPayment']", 'null': 'True', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']"}),
            'job_task': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'sub_status': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Worker']"})
        }
    }

    complete_apps = ['payments']