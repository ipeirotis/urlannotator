import odesk
import hashlib
import string
import random
import os
import csv
import json

from docutils import core
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.template import RequestContext, Context
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template.loader import get_template
from django.views.decorators.cache import cache_page
from django.conf import settings
from itertools import ifilter
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow

from urlannotator.main.forms import (WizardTopicForm, WizardAttributesForm,
    WizardAdditionalForm, NewUserForm, UserLoginForm, AlertsSetupForm,
    GeneralEmailUserForm, GeneralUserForm, BTMForm)
from urlannotator.main.models import (Account, Job, Worker, Sample,
    LABEL_YES, LABEL_NO, LABEL_BROKEN)
from urlannotator.statistics.stat_extraction import (extract_progress_stats,
    extract_url_stats, extract_spent_stats, extract_performance_stats,
    extract_votes_stats)
from urlannotator.classification.models import (ClassifierPerformance,
    ClassifiedSample, TrainingSet)
from urlannotator.logging.models import LogEntry, LongActionEntry


def get_activation_key(email, num, salt_size=10,
                       salt_chars=string.ascii_uppercase + string.digits):
    """
        Generates an activation key for email account activation. It is later
        sent to user's email.
    """
    key = hashlib.sha1()
    salt = ''.join(random.choice(salt_chars) for x in range(salt_size))
    key.update('%s%s%d' % (salt, email, num))
    return '%s-%d' % (key.hexdigest(), num)


@login_required
def alerts_view(request):
    def aggregate(entry_set, attribute):
        entry_dict = {}
        for entry in entry_set:
            entry_type = getattr(entry, attribute)
            if entry_type in entry_dict:
                entry_dict[entry_type] = entry.get_plural_text()
            else:
                entry_dict[entry_type] = entry.get_single_text()
        return entry_dict

    alert_entries = LogEntry.objects.unread_for_user(request.user)
    alerts = aggregate(alert_entries, 'log_type')

    action_entries = LongActionEntry.objects.running_for_user(request.user)
    actions = aggregate(action_entries, 'action_type')
    res = {
        'alerts': alerts,
        'actions': actions,
    }
    return HttpResponse(json.dumps(res))


@login_required
def updates_box_view(request, job_id):
    if job_id == '0' and request.user.is_superuser:
        log_entries = LogEntry.objects.recent_for_job(num=0)
        res = [entry.get_box() for entry in log_entries]
    else:
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'Project doesn\'t exist'})
            )

        if (job.account != request.user.get_profile()
                and not request.user.is_superuser):
            return HttpResponse(
                json.dumps({'error': 'Project doesn\'t exist'})
            )

        log_entries = LogEntry.objects.recent_for_job(
            job=job,
            num=4,
        )
        res = [entry.get_box() for entry in log_entries]

    return HttpResponse(json.dumps(res))


def sample_thumbnail(request, id, thumb_type=None, width=0, height=0):
    try:
        sample = Sample.objects.get(id=id)
    except Sample.DoesNotExist:
        raise Http404

    if thumb_type is None and width and height:
        return HttpResponse(
            sample.get_thumbnail(width=width, height=height),
            content_type='image/png'
        )
    elif thumb_type == 'small':
        return HttpResponse(
            sample.get_small_thumbnail(),
            content_type='image/png'
        )
    else:
        return HttpResponse(
            sample.get_large_thumbnail(),
            content_type='image/png'
        )


@csrf_protect
def register_view(request):
    """
        If the request's method is GET - serves all registration forms.
        POST requests are handling e-mail registration.
    """
    if request.method == "GET":
        context = {'form': NewUserForm()}
        error = request.session.pop('error', None)
        if error:
            context['error'] = error

        return render(request, 'main/register.html',
            RequestContext(request, context))
    else:
        form = NewUserForm(request.POST)
        context = {'form': form}
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'])
            user.is_active = False
            user.save()
            subjectTemplate = get_template('activation_email_subject.txt')
            bodyTemplate = get_template('activation_email.txt')
            key = get_activation_key(form.cleaned_data['email'],
                user.get_profile().id)
            user.get_profile().activation_key = key
            user.get_profile().email_registered = True
            user.get_profile().save()
            cont = Context({'key': key, 'site': settings.SITE_URL})
            send_mail(subjectTemplate.render(cont).replace('\n', ''),
                bodyTemplate.render(cont), 'URL Annotator', [user.email])
            context = {'success': ('Thanks for registering. '
                'An activation email has been sent '
                'to %s with further instructions.') % user.email,
                'login_view': True,
                'form':UserLoginForm()}
            return render(request, 'main/login.html',
                RequestContext(request, context))

        return render(request, 'main/register.html',
            RequestContext(request, context))


def register_service(request, service):
    request.session['registration'] = service
    return redirect('socialauth_begin', service)


def odesk_register(request):
    return redirect('odesk_login')


def logout_view(request):
    logout(request)
    return redirect('index')


def activation_view(request, key):
    prof_id = key.rsplit('-', 1)
    context = {}
    if len(prof_id) != 2:
        context = {'error': 'Wrong activation key.'}
        return render(request, 'main/login.html',
            RequestContext(request, context))

    try:
        prof = Account.objects.get(id=int(prof_id[1]))
    except Account.DoesNotExist:
        context = {'error': 'Wrong activation key.'}
        return render(request, 'main/login.html',
            RequestContext(request, context))

    if prof.activation_key != key:
        context = {'error': 'Wrong activation key.'}
        return render(request, 'main/login.html',
            RequestContext(request, context))
    prof.user.is_active = True
    prof.user.save()
    prof.activation_key = 'activated'
    prof.save()
    context = { 'success': 'Your account has been activated.',
                'form':UserLoginForm()}
    return render(request, 'main/login.html',
        RequestContext(request, context))


@csrf_protect
def login_view(request):
    context = {'login_view': True}
    if request.method == "GET":
        context['form'] = UserLoginForm()
        error = request.session.pop('error', None)
        if error:
            context['error'] = error
        return render(request, 'main/login.html',
            RequestContext(request, context))
    else:
        form = UserLoginForm(request.POST)
        context['form'] = form
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['email'],
                password=form.cleaned_data['password'])
            if user is not None:
                if not user.get_profile().email_registered:
                    context['error'] = ('Username and/or password is incorrect.')
                    return render(request, 'main/login.html',
                        RequestContext(request, context))

                if user.is_active:
                    login(request, user)
                    if 'remember' in request.POST:
                        request.session.set_expiry(0)
                    request.session['success'] = ('You are logged in')
                    redirect('index')
                else:
                    context['error'] = ('This account is still inactive.')
                    return render(request, 'main/login.html',
                        RequestContext(request, context))
            else:
                context['error'] = ('Username and/or password is incorrect.')
                return render(request, 'main/login.html',
                    RequestContext(request, context))
        else:
            context['error'] = ('Username and/or password is incorrect.')
            return render(request, 'main/login.html',
                RequestContext(request, context))
    return redirect('index')


@login_required
def settings_view(request):
    profile = request.user.get_profile()
    context = {}

    if profile.email_registered:
        context['general_form'] = GeneralEmailUserForm(
            {'email': request.user.email, 'full_name': profile.full_name})
        context['password_form'] = PasswordChangeForm(request.user)
    else:
        context['general_form'] = GeneralUserForm(
            {'full_name': profile.full_name})

    context['alerts_form'] = AlertsSetupForm({'alerts': profile.alerts})
    l = request.user.social_auth.filter(provider='facebook')
    if l:
        context['facebook'] = l[0]
    l = request.user.social_auth.filter(provider='google-oauth2')
    if l:
        context['google'] = l[0]
    l = request.user.social_auth.filter(provider='twitter')
    if l:
        context['twitter'] = l[0]

    if profile.odesk_uid:
        w = Worker.objects.get(external_id=profile.odesk_uid)
        context['odesk'] = {'name': w.get_name()}

    if request.method == "POST":
        if 'submit' in request.POST:
            if request.POST['submit'] == 'general':
                if profile.email_registered:
                    form = GeneralEmailUserForm(request.POST)
                    if form.is_valid():
                        profile.full_name = form.cleaned_data['full_name']
                        profile.save()
                        context['success'] = (
                            'Full name has been successfully changed.')
                    else:
                        context['general_form'] = form
                else:
                    form = GeneralUserForm(request.POST)
                    if form.is_valid():
                        profile.full_name = form.cleaned_data['full_name']
                        profile.save()
                        context['success'] = (
                            'Full name has been successfully changed.')
                    else:
                        context['general_form'] = form
            elif request.POST['submit'] == 'password':
                form = PasswordChangeForm(request.user, request.POST)
                if form.is_valid():
                    form.save()
                    context['success'] = (
                        'Password has been successfully changed.')
                else:
                    context['password_form'] = form
            elif request.POST['submit'] == 'alerts':
                form = AlertsSetupForm(request.POST)
                if form.is_valid():
                    profile.alerts = form.cleaned_data['alerts']
                    profile.save()
                    context['success'] = (
                        'Alerts setup has been successfully changed.')
                else:
                    context['alerts_form'] = form
    return render(request, 'main/settings.html',
        RequestContext(request, context))


@login_required
def project_wizard(request):
    odeskLogged = request.user.get_profile().odesk_uid != ''
    if request.method == "GET":
        context = {'topic_form': WizardTopicForm(),
                   'attributes_form': WizardAttributesForm(odeskLogged),
                   'additional_form': WizardAdditionalForm()}
        if not odeskLogged:
            context['wizard_alert'] = ('Your account is not connected to '
                'Odesk. If you want to have more options connect to Odesk at '
                '<a href="%s">settings</a> page.') % reverse('settings')
    else:
        topic_form = WizardTopicForm(request.POST)
        attr_form = WizardAttributesForm(odeskLogged, request.POST)
        addt_form = WizardAdditionalForm(request.POST, request.FILES)
        is_draft = request.POST['submit'] == 'draft'

        context = {'topic_form': topic_form,
                   'attributes_form': attr_form,
                   'additional_form': addt_form}

        if not odeskLogged:
            context['wizard_alert'] = ('Your account is not connected to '
                'Odesk. If you want to have more options connect to Odesk at '
                '<a href="%s">settings</a> page.') % reverse('settings')

        if (addt_form.is_valid() and
                attr_form.is_valid() and
                topic_form.is_valid()):
            params = {
                'account': request.user.get_profile(),
                'title': topic_form.cleaned_data['topic'],
                'description': topic_form.cleaned_data['topic_desc'],
                'data_source': attr_form.cleaned_data['data_source'],
                'project_type': attr_form.cleaned_data['project_type'],
                'no_of_urls': attr_form.cleaned_data['no_of_urls'],
                'hourly_rate': attr_form.cleaned_data['hourly_rate'],
                'budget': attr_form.cleaned_data['budget'],
                'same_domain_allowed': addt_form.cleaned_data['same_domain'],
            }
            if not params['no_of_urls']:
                params['no_of_urls'] = 0

            if 'file_gold_urls' in request.FILES:
                url_set = set()
                label_set = set()
                try:
                    urls = csv.reader(request.FILES['file_gold_urls'])
                    gold_samples = []
                    for line in urls:
                        url = line[0]
                        label = line[1]
                        if url in url_set:
                            continue

                        url_set.add(url)
                        label_set.add(label)
                        gold_samples.append({'url': url, 'label': label})

                    if len(url_set) < 6:
                        context['wizard_error'] = (
                            'You have to provide at least 6 different '
                            'gold samples.'
                        )
                        return render(request, 'main/project/wizard.html',
                            RequestContext(request, context))

                    if len(label_set) < 2:
                        context['wizard_error'] = (
                            'You have to provide at least 2 different labels.'
                        )
                        return render(request, 'main/project/wizard.html',
                            RequestContext(request, context))

                    params['gold_samples'] = json.dumps(gold_samples)

                except csv.Error, e:
                    request.session['error'] = e
                    return redirect('index')

            if 'file_classify_urls' in request.FILES:
                try:
                    urls = csv.reader(request.FILES['file_classify_urls'])
                    classify_urls = [line[0] for line in urls]
                    params['classify_urls'] = json.dumps(classify_urls)
                except csv.Error, e:
                    request.session['error'] = e
                    return redirect('index')

            if is_draft:
                job = Job.objects.create_draft(**params)
            else:
                job = Job.objects.create_active(**params)

            return redirect('project_view', id=job.id)
    return render(request, 'main/project/wizard.html',
        RequestContext(request, context))


@login_required
def odesk_disconnect(request):
    request.user.get_profile().odesk_uid = ''
    request.user.get_profile().odesk_key = ''
    request.user.get_profile().save()
    return redirect('index')


def odesk_complete(request):
    client = odesk.Client(
        settings.ODESK_CLIENT_ID,
        settings.ODESK_CLIENT_SECRET
    )
    auth, user = client.auth.get_token(request.GET['frob'])
    client = odesk.Client(
        settings.ODESK_CLIENT_ID,
        settings.ODESK_CLIENT_SECRET,
        auth,
    )
    info = client.auth.my_info()
    url = info['info']['profile_url']
    # Extract the ciphertext from the profile url. This should be provided by
    # API, no?
    cipher = url.rsplit('/', 1)[1]

    if request.user.is_authenticated():
        if request.user.get_profile().odesk_uid == '':
            request.user.get_profile().odesk_uid = cipher
            request.user.get_profile().odesk_key = auth
            request.user.get_profile().save()

            # Add Worker model on odesk account association
            if not Worker.objects.filter(external_id=cipher):
                Worker.objects.create_odesk(external_id=cipher)
            request.session['success'] = 'You have successfully logged in.'
        return redirect('index')
    else:
        try:
            assoc = Account.objects.get(odesk_uid=cipher)
            u = authenticate(username=assoc.user.username, password='1')
            login(request, u)
            return redirect('index')
        except Account.DoesNotExist:
            u = User.objects.create_user(email=user['mail'],
                username=' '.join(['odesk', cipher]), password='1')
            profile = u.get_profile()
            profile.odesk_uid = cipher
            profile.odesk_key = auth
            profile.full_name = '%s %s' % (user['first_name'],
                user['last_name'])
            profile.save()
            u = authenticate(username=u.username, password='1')
            login(request, u)

            # Create Worker model on odesk account registration
            if not Worker.objects.filter(external_id=cipher):
                Worker.objects.create_odesk(external_id=cipher)
            request.session['success'] = 'You have successfuly registered'
            return redirect('settings')


@login_required
def debug_prediction_complete(request):
    storage = Storage('prediction.dat')
    flow = request.session.get('flow', None)
    if not flow:
        return redirect('index')

    credentials = flow.step2_exchange(request.GET)
    storage.put(credentials)

    request.session.pop('flow')
    request.session['success'] = 'Google Prediction has been added.'
    return redirect('index')


@login_required
def debug_prediction(request):
    flow = OAuth2WebServerFlow(
        settings.GOOGLE_PREDICTION_ID,
        settings.GOOGLE_PREDICTION_SECRET,
        'https://www.googleapis.com/auth/prediction',
        None,  # user_agent
        'https://accounts.google.com/o/oauth2/auth',
        'https://accounts.google.com/o/oauth2/token')

    storage = Storage('prediction.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        request.session['flow'] = flow
        return redirect(flow.step1_get_authorize_url(
            redirect_uri='http://%s%s' % (
                settings.SITE_URL,
                reverse('debug_prediction_complete')
            )))
    request.session['success'] = 'Google Prediction is still valid.'
    return redirect('index')


def debug_login(request):
    user = authenticate(username='test', password='test')
    if user is None:
        user = User.objects.create_user(username='test', email='test@test.com',
            password='test')
        user.is_superuser = True
        user.save()
        prof = user.get_profile()
        prof.email_registered = True
        prof.activation_key = 'activated'
        prof.save()
    user = authenticate(username='test', password='test')
    login(request, user)
    request.session['success'] = 'You have successfully logged in.'
    return redirect('index')


@login_required
def debug_superuser(request):
    request.user.is_superuser = True
    request.user.save()
    request.session['success'] = 'You are now superuser.'
    return redirect('index')


def odesk_login(request):
    client = odesk.Client(settings.ODESK_CLIENT_ID,
        settings.ODESK_CLIENT_SECRET)
    return redirect(client.auth.auth_url())


@login_required
def project_view(request, id):
    try:
        proj = Job.objects.get(id=id)
    except Job.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if (proj.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if request.method == "POST":
        value = request.POST.get('submit', None)
        if value == 'Activate project':
            if proj.is_draft():
                proj.initialize()

    context = {'project': proj}
    extract_progress_stats(proj, context)
    extract_url_stats(proj, context)
    extract_spent_stats(proj, context)
    extract_performance_stats(proj, context)
    extract_votes_stats(proj, context)
    context['hours_spent'] = proj.get_hours_spent()
    context['urls_collected'] = proj.get_urls_collected()
    context['no_of_workers'] = proj.get_no_of_workers()
    context['cost'] = proj.get_cost()
    context['budget'] = proj.budget
    context['progress_urls'] = proj.get_progress_urls()
    context['progress_votes'] = proj.get_progress_votes()

    return render(request, 'main/project/overview.html',
        RequestContext(request, context))


@login_required
def project_workers_view(request, id):
    try:
        job = Job.objects.get(id=id)
    except Job.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if (job.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    context = {'project': job}
    workers = []
    for worker in job.get_workers():
        workers.append({
            'id': worker.id,
            'name': worker.get_name,
            'quality': worker.get_estimated_quality_for_job(job),
            'votes_added': worker.get_votes_added_count_for_job(job),
            'urls_collected': worker.get_urls_collected_count_for_job(job),
            'hours_spent': worker.get_hours_spent_for_job(job)
        })
    context['workers'] = workers
    return render(request, 'main/project/workers.html',
        RequestContext(request, context))


@login_required
def project_worker_view(request, id, worker_id):
    try:
        job = Job.objects.get(id=id)
        worker = Worker.objects.get(id=worker_id)
    except (Job.DoesNotExist, Worker.DoesNotExist):
        request.session['error'] = 'The user does not exist.'
        return redirect('index')

    if not worker.can_show_to_user():
        request.session['error'] = 'The user does not exist.'
        return redirect('index')

    if (job.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    context = {'project': job}
    account = request.user.get_profile()
    assocs = worker.workerjobassociation_set.all()
    assocs = ifilter(lambda x: x.job.account == account, assocs)
    projects = (w.job.get_link_with_title() for w in assocs)
    context['worker'] = {
        'name': worker.get_name,
        'urls_collected': worker.get_urls_collected_count_for_job(job),
        'votes_added': worker.get_votes_added_count_for_job(job),
        'hours_spent': worker.get_hours_spent_for_job(job),
        'quality': worker.get_estimated_quality_for_job(job),
        'earned': worker.get_earned_for_job(job),
        'work_started': worker.get_job_start_time(job),
        'projects': projects,
    }
    return render(request, 'main/project/worker.html',
        RequestContext(request, context))


@login_required
def project_debug(request, id, debug):
    try:
        proj = Job.objects.get(id=id)

    except Job.DoesNotExist:
        request.session['error'] = "Such project doesn't exist."
        return redirect('index')

    if (proj.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if debug == 'draft':
        proj.project_status = 0
    elif debug == 'active':
        proj.activate()
    elif debug == 'completed':
        proj.stop()
    else:
        request.session['error'] = "Wrong debug parameter."
        return redirect('index')

    proj.save()
    request.session['success'] = 'Job status successfully changed.'
    return redirect('index')


@login_required
def project_btm_view(request, id):
    try:
        job = Job.objects.get(id=id)
    except Job.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if (job.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    context = {'project': job}
    if job.is_btm_active():
        context['pending_samples'] = job.get_btm_pending_samples()
        return render(request, 'main/project/btm_view.html',
            RequestContext(request, context))
    else:
        context['form'] = BTMForm()
        if request.method == 'POST':
            form = BTMForm(request.POST)
            if form.is_valid():
                job.start_btm(
                    topic=form.cleaned_data['topic'],
                    description=form.cleaned_data['topic_desc'],
                    no_of_urls=form.cleaned_data['no_of_urls'],
                )
                return redirect('project_btm_view', id=id)
            context['form'] = form
        return render(request, 'main/project/btm.html',
            RequestContext(request, context))


@login_required
def project_data_view(request, id):
    try:
        job = Job.objects.get(id=id)
    except Job.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if (job.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    context = {
        'project': job,
        'data_set': (sample for sample in Sample.objects.filter(job=job,
            btm_sample=False) if sample.is_finished()),
    }

    return render(request, 'main/project/data.html',
        RequestContext(request, context))


@login_required
def project_data_detail(request, id, data_id):
    try:
        job = Job.objects.get(id=id)
        sample = Sample.objects.get(id=data_id, job=job)
    except (Job.DoesNotExist, Sample.DoesNotExist):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if (job.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    context = {
        'project': job,
        'sample': sample,
    }
    return render(request, 'main/project/data_detail.html',
        RequestContext(request, context))


@csrf_protect
@login_required
def project_classifier_view(request, id):
    try:
        job = Job.objects.get(id=id)
    except Job.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if (job.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    context = {'project': job}

    if request.method == "GET":
        classified_samples = request.session.get('classified-samples', [])
        samples_pending = []
        samples_created = []

        classified_samples = ClassifiedSample.objects.filter(job=job,
            id__in=classified_samples)
        for sample in classified_samples:
            if not sample.sample:
                samples_pending.append(sample)
            else:
                samples_created.append(sample)

        context['samples_pending'] = samples_pending
        context['samples_created'] = samples_created

    elif request.method == "POST":
        test_type = request.POST.get('test-type', 'urls')
        if test_type == 'urls':
            urls = request.POST.get('test-urls', '')
            # Split text to lines with urls, and remove duplicates
            urls = set(urls.splitlines())
            classified_samples = []
            for url in urls:
                cs = ClassifiedSample.objects.create_by_owner(
                    job=job,
                    url=url
                )
                classified_samples.append(cs.id)
            request.session['classified-samples'] = classified_samples
        return redirect('project_classifier_view', id)
    yes_labels = []
    no_labels = []

    for sample in job.sample_set.all().iterator():
        label = sample.get_classified_label()
        if label == LABEL_YES:
            yes_labels.append(sample)
        elif label == LABEL_NO:
            no_labels.append(sample)

    yc = len(yes_labels)
    nc = len(no_labels)
    yes_perc = int(yc * 100 / ((yc + nc) or 1))
    no_perc = int(nc * 100 / ((yc + nc) or 1))
    context['classifier_stats'] = {
        'count': yc + nc,
        'yes_labels': {'val': yc, 'perc': yes_perc},
        'no_labels': {'val': nc, 'perc': no_perc},
        'broken_labels': {'val': 0, 'perc': 0}}

    context['performance_TPR'] = []
    context['performance_TNR'] = []
    context['performance_AUC'] = []
    for perf in ClassifierPerformance.objects.filter(job=job).order_by('date'):
        date = perf.date.strftime('%Y,%m-1,%d,%H,%M,%S')
        context['performance_TPR'].append(
            '[Date.UTC(%s),%f]' % (date, perf.value.get('TPR', 0)))
        context['performance_TNR'].append(
            '[Date.UTC(%s),%f]' % (date, perf.value.get('TNR', 0)))
        context['performance_AUC'].append(
            '[Date.UTC(%s),%f]' % (date, perf.value.get('AUC', 0)))

    context['performance_TPR'] = ','.join(context['performance_TPR'])
    context['performance_TNR'] = ','.join(context['performance_TNR'])
    context['performance_AUC'] = ','.join(context['performance_AUC'])
    return render(request, 'main/project/classifier.html',
        RequestContext(request, context))


@login_required
def project_classifier_data(request, id):
    try:
        job = Job.objects.get(id=id)
    except Job.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    if (job.account != request.user.get_profile()
            and not request.user.is_superuser):
        request.session['error'] = 'The project does not exist.'
        return redirect('index')

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=training_data.csv'

    writer = csv.writer(response)
    training_set = TrainingSet.objects.newest_for_job(job=job)
    for sample in training_set.training_samples.all():
        writer.writerow([sample.sample.url, sample.label])

    return response


def doc_parts(input_string):
    parts = core.publish_parts(source=input_string, writer_name='html')
    return parts


@cache_page(10 * 60)
def readme_view(request):
    file_path = os.path.join(settings.ROOT_DIR, '..', 'readme.rst')
    with open(file_path, 'r') as file:
        parts = doc_parts(file.read())
        context = {'content': parts['html_body']}
        return render(request, 'main/docs.html', RequestContext(request, context))


@login_required
def admin_index(request):
    """
        Listing of all jobs across the system. Usable only by superusers.
    """
    if not request.user.is_superuser:
        raise Http404

    context = {
        'projects': Job.objects.all().order_by('-id'),
    }
    return render(request, 'main/admin_index.html',
        RequestContext(request, context))


def index(request):
    context = {}
    if 'error' in request.session:
        context['error'] = request.session['error']
        request.session.pop('error')
    if 'success' in request.session:
        context['success'] = request.session['success']
        request.session.pop('success')

    if request.user.is_authenticated():
        context['projects'] = Job.objects.filter(
            account=request.user.get_profile()).order_by('-id')
        return render(request, 'main/index.html', RequestContext(request, context))
    else:
        return render(request, 'main/landing.html', RequestContext(request, context))


def hit(request):
    context = {}

    return render(request, 'main/hit/hit.html', RequestContext(request, context))
