# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'OdeskJob.user_id'
        db.add_column('crowdsourcing_odeskjob', 'user_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=128),
                      keep_default=False)

        # Adding field 'OdeskJob.engagement_id'
        db.add_column('crowdsourcing_odeskjob', 'engagement_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=128),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'OdeskJob.user_id'
        db.delete_column('crowdsourcing_odeskjob', 'user_id')

        # Deleting field 'OdeskJob.engagement_id'
        db.delete_column('crowdsourcing_odeskjob', 'engagement_id')


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
        'crowdsourcing.beatthemachinesample': {
            'Meta': {'object_name': 'BeatTheMachineSample'},
            'added_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'btm_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'expected_output': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'frozen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'human_label': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']"}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'label_probability': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
            'payment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['payments.BTMBonusPayment']", 'null': 'True', 'blank': 'True'}),
            'points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'sample': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Sample']", 'null': 'True', 'blank': 'True'}),
            'source_type': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'source_val': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'crowdsourcing.odeskjob': {
            'Meta': {'object_name': 'OdeskJob'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'declined': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'engagement_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'meta_job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crowdsourcing.OdeskMetaJob']"}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'worker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Worker']", 'null': 'True', 'blank': 'True'})
        },
        'crowdsourcing.odeskmetajob': {
            'Meta': {'object_name': 'OdeskMetaJob'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Account']"}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hit_reference': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']", 'null': 'True', 'blank': 'True'}),
            'job_type': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'reference': ('django.db.models.fields.CharField', [], {'max_length': '64', 'primary_key': 'True'}),
            'workers_to_invite': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'crowdsourcing.samplemapping': {
            'Meta': {'object_name': 'SampleMapping'},
            'crowscourcing_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sample': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Sample']"})
        },
        'crowdsourcing.tagasaurisjobs': {
            'Meta': {'object_name': 'TagasaurisJobs'},
            'beatthemachine_hit': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'beatthemachine_key': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sample_gathering_hit': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'sample_gathering_key': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'urlannotator_job': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['main.Job']", 'unique': 'True'}),
            'voting_btm_hit': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'voting_btm_key': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'voting_hit': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'voting_key': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'crowdsourcing.troiajob': {
            'Meta': {'object_name': 'TroiaJob'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['main.Job']", 'unique': 'True'}),
            'troia_id': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'crowdsourcing.workerqualityvote': {
            'Meta': {'unique_together': "(['worker', 'sample'],)", 'object_name': 'WorkerQualityVote'},
            'added_on': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'btm_vote': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_new': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
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
            'odesk_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'odesk_secret': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'odesk_teams': ('tenclouds.django.jsonfield.fields.JSONField', ['{}'], {'blank': 'True'}),
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
        'main.sample': {
            'Meta': {'unique_together': "(('job', 'url'),)", 'object_name': 'Sample'},
            'added_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'btm_sample': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Job']"}),
            'screenshot': ('django.db.models.fields.URLField', [], {'max_length': '500'}),
            'source_type': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'source_val': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'training': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '500'}),
            'vote_sample': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
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
        }
    }

    complete_apps = ['crowdsourcing']