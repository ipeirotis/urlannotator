from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.template import RequestContext, Context
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponse
import odesk
from django.template.loader import get_template
import hashlib
import os

from urlannotator.main.forms import WizardTopicForm, WizardAttributesForm,\
    WizardAdditionalForm, NewUserForm, UserLoginForm, AlertsSetupForm,\
    GeneralEmailUserForm, GeneralUserForm
from urlannotator.main.models import UserProfile, UserOdeskAssociation, Project
from urlannotator.settings.defaults import ODESK_CLIENT_ID, ODESK_CLIENT_SECRET,\
    ROOT_DIR, SITE_URL

def get_activation_key(email, num):
    key = hashlib.sha1()
    key.update('%s%s%s%d' % ('thereisn', email, 'ospoon', num))
    return '%s-%d' % (key.hexdigest(), num)
        
@csrf_protect
def register_view(request):
    if request.method == "GET":
        context = {'form': NewUserForm()}
        return render(request, 'main/register.html', RequestContext(request, context))
    else:
        form = NewUserForm(request.POST)
        context = {'form': form}
        if form.is_valid():
            user = User.objects.create_user(username=form.cleaned_data['email'], email=form.cleaned_data['email'], password=form.cleaned_data['password1'])
            user.is_active = False
            user.save()
            subjectTemplate = get_template('activation_email_subject.txt')
            bodyTemplate = get_template('activation_email.txt')
            key = get_activation_key(form.cleaned_data['email'], user.get_profile().id)
            user.get_profile().activation_key = key
            user.get_profile().email_registered = True
            user.get_profile().save()
            cont = Context({'key': key, 'site': SITE_URL})
            send_mail(subjectTemplate.render(cont).replace('\n', ''), bodyTemplate.render(cont), 'URL Annotator', [user.email])
            return redirect('index')

        return render(request, 'main/register.html', RequestContext(request, context))

def register_service(request, service):
    request.session['registration'] = service
    return redirect('socialauth_begin', service)

def odesk_register(request):
    request.session['registration'] = 'odesk'
    return redirect('odesk_login')    
    
def logout_view(request):
    logout(request)
    return redirect('index')

def activation_view(request, key):
    prof_id = key.rsplit('-', 1)
    if len(prof_id) != 2:
        context = {'error': 'Wrong activation key.'}
        return render(request, 'main/index.html', RequestContext(request, context))

    try:
        prof = UserProfile.objects.get(id=int(prof_id[1]))
    except UserProfile.DoesNotExist:
        context = {'error': 'Wrong activation key.'}
        return render(request, 'main/index.html', RequestContext(request, context))

    if not prof:
        context = {'error': 'Wrong activation key.'}
        return render(request, 'main/index.html', RequestContext(request, context))
    else:
        if prof.activation_key != key:
            context = {'error': 'Wrong activation key.'}
            return render(request, 'main/index.html', RequestContext(request, context))
        prof.user.is_active = True
        prof.user.save()
        prof.activation_key = 'activated'
        prof.save()
        context = {'success': 'Your account has been activated.'}
        return render(request, 'main/index.html', RequestContext(request, context))
    return redirect('index')

@csrf_protect
def login_view(request):
    if request.method == "GET":
        context = {'form': UserLoginForm()}
        return render(request, 'main/login.html', RequestContext(request, context))
    else:
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['email'], password=form.cleaned_data['password'])
            if user is not None:
                if not user.get_profile().email_registered:
                    request.session['error'] = 'Username and/or password is incorrect.'
                    return redirect('index')

                if user.is_active:
                    login(request, user)
                    if 'remember' in request.POST:
                        request.session.set_expiry(0)
                    return redirect('index')
                else:
                    context = {'error': 'This account is still inactive.'}
                    return render(request, 'main/index.html', RequestContext(request, context))
            else:
                request.session['error'] = 'Username and/or password is incorrect.'
                return redirect('index')
        else:
            context = {'error': 'Username and/or password is incorrect.'}
            return render(request, 'main/index.html', RequestContext(request, context))
    return redirect('index')

@login_required
def settings(request):
    profile = request.user.get_profile()
    context = {}
    
    if profile.email_registered:
        context['general_form'] = GeneralEmailUserForm({'email': request.user.email, 'full_name': profile.full_name})
        context['password_form'] = PasswordChangeForm(request.user)
    else:
        context['general_form'] = GeneralUserForm({'full_name': profile.full_name})

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
    
    u = UserOdeskAssociation.objects.filter(user=request.user)
    if u:
        context['odesk'] = {'name': u[0].full_name}

    if request.method == "POST":
        if 'submit' in request.POST:
            if request.POST['submit'] == 'general':
                if profile.email_registered:
                    form = GeneralEmailUserForm(request.POST)
                    if form.is_valid():
                        profile.full_name = form.cleaned_data['full_name']
                        profile.save()
                        context['success'] = 'Full name has been successfully changed.'
                    else:
                        context['general_form'] = form
                else:
                    form = GeneralUserForm(request.POST)
                    if form.is_valid():
                        profile.full_name = form.cleaned_data['full_name']
                        profile.save()
                        context['success'] = 'Full name has been successfully changed.'
                    else:
                        context['general_form'] = form
            elif request.POST['submit'] == 'password':
                form = PasswordChangeForm(request.user, request.POST)
                if form.is_valid():
                    form.save()
                    context['success'] = 'Full name has been successfully changed.'
                else:
                    context['password_form'] = form
            elif request.POST['submit'] == 'alerts':
                form = AlertsSetupForm(request.POST)
                if form.is_valid():
                    profile.alerts = form.cleaned_data['alerts']
                    profile.save()
                    context['success'] = 'Alerts setup has been successfully changed.'
                else:
                    context['alerts_form'] = form
    return render(request, 'main/settings.html', RequestContext(request, context))

@login_required
def project_wizard(request):
    odeskLogged = UserOdeskAssociation.objects.filter(user=request.user).count() != 0
    if request.method == "GET":
        context = {'topic_form': WizardTopicForm(),
                   'attributes_form': WizardAttributesForm(odeskLogged),
                   'additional_form': WizardAdditionalForm()}
        if not odeskLogged:
            context['wizard_alert'] = '''Your account is not connected to Odesk.
                                         If you want to have more options connect to Odesk at 
                                         <a href="%s">settings</a> page.''' % reverse('settings')
    else:
        topic_form = WizardTopicForm(request.POST)
        attr_form = WizardAttributesForm(odeskLogged, request.POST)
        addt_form = WizardAdditionalForm(request.POST)
        if request.POST['submit'] == 'draft':
            p_type = 0
        else:
            p_type = 1
        if addt_form.is_valid() and attr_form.is_valid() and topic_form.is_valid():
            p = Project(author=request.user,
                        topic=topic_form.cleaned_data['topic'],
                        topic_desc=topic_form.cleaned_data['topic_desc'],
                        data_source=attr_form.cleaned_data['data_source'],
                        project_type=attr_form.cleaned_data['project_type'],
                        no_of_urls=attr_form.cleaned_data['no_of_urls'], 
                        hourly_rate=attr_form.cleaned_data['hourly_rate'],
                        budget=attr_form.cleaned_data['budget'],
                        same_domain_allowed=addt_form.cleaned_data['same_domain'],
                        project_status=p_type)
            p.save()
            return redirect('project_view', id=p.id)
        context = {'topic_form': topic_form,
                   'attributes_form': attr_form,
                   'additional_form': addt_form}
        if not odeskLogged:
            context['wizard_alert'] = "Your account is not connected to Odesk. If you want to have more options connect to Odesk at settings page."
    return render(request, 'main/project/wizard.html', RequestContext(request, context))
  
@login_required
def odesk_disconnect(request):
    assoc = UserOdeskAssociation.objects.filter(user=request.user)
    if assoc:
        assoc.delete()
    return redirect('index')

def odesk_complete(request):
    client = odesk.Client(ODESK_CLIENT_ID, ODESK_CLIENT_SECRET)
    auth, user = client.auth.get_token(request.GET['frob'])
      
    if request.user.is_authenticated():
        assoc = UserOdeskAssociation.objects.filter(user=request.user, uid=user['uid'])
        if not assoc:
            u = request.user
            # Logged user odesk account association
            assoc = UserOdeskAssociation(user=u, uid=user['uid'], token=auth, full_name=' '.join([user['first_name'], user['last_name']]))
            assoc.save()
            request.session['success'] = 'You have successfully logged in.'
        return redirect('index')
    else:
        assoc = UserOdeskAssociation.objects.filter(uid=user['uid'])
        u = None
        if assoc:
            u = authenticate(username=assoc[0].user.username, password='1')
        else:
            # if the user is registering, create a new association, otherwise show alert that the account
            # has not been registered with
            if not 'registration' in request.session:
                request.session['error'] = "Account for that social media doesn't exist. Please register first."
                return redirect('index')
            request.session.pop('registration')

        if u is None:
            u = User.objects.create_user(email=user['mail'], username=' '.join(['odesk', user['uid']]), password='1')
            u.get_profile().full_name = '%s %s' % (user['first_name'], user['last_name'])
            u.get_profile().save()
            assoc = UserOdeskAssociation(user=u, uid=user['uid'], token=auth, full_name=u.get_profile().full_name)
            assoc.save()
            u = authenticate(username=u.username, password='1')
            request.session['success'] = 'You have successfuly registered'
        login(request, u)
        return redirect('index')

def debug_login(request):
    user = authenticate(username='test', password='test')
    if user is None:
        user = User.objects.create_user(username='test', email='test@test.com', password='test')
        prof = user.get_profile()
        prof.email_registered = True
        prof.activation_key = 'activated'
        prof.save()
    user = authenticate(username='test', password='test')
    login(request, user)
    request.session['success'] = 'You have successfully logged in.'
    return redirect('index')

def odesk_login(request):
    client = odesk.Client(ODESK_CLIENT_ID, ODESK_CLIENT_SECRET)
    return redirect(client.auth.auth_url())

@login_required
def project_view(request, id):
    try:
        proj = Project.objects.get(id=id)
    except Project.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')
    
    context = {'project': proj}
    return render(request, 'main/project/overview.html', RequestContext(request, context)) 

@login_required
def project_workers_view(request, id):
    try:
        proj = Project.objects.get(id=id)
    except Project.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')
    
    context = {'project': proj}
    return render(request, 'main/project/workers.html', RequestContext(request, context))

@login_required
def project_worker_view(request, id, worker_id):
    try:
        proj = Project.objects.get(id=id)
    except Project.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')
    
    context = {'project': proj}
    return render(request, 'main/project/worker.html', RequestContext(request, context))

@login_required
def project_debug(request, id, debug):
    try:
        proj = Project.objects.get(id=id)
    except Project.DoesNotExist:
        request.session['error'] = "Such project doesn't exist."
        return redirect('index')
    
    if debug == 'draft':
        proj.project_status = 0
    elif debug == 'active':
        proj.project_status = 1
    elif debug == 'completed':
        proj.project_status = 2
    else:
        request.session['error'] = "Wrong debug parameter."
        return redirect('index')
    
    proj.save()
    request.session['success'] = 'Project status successfully changed.'
    return redirect('index')
    
@login_required
def project_btm_view(request, id):
    try:
        proj = Project.objects.get(id=id)
    except Project.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')
    
    context = {'project': proj}
    return render(request, 'main/project/btm_view.html', RequestContext(request, context))

@login_required
def project_data_view(request, id):
    try:
        proj = Project.objects.get(id=id)
    except Project.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')
    
    context = {'project': proj}
    return render(request, 'main/project/data.html', RequestContext(request, context)) 

@login_required
def project_classifier_view(request, id):
    try:
        proj = Project.objects.get(id=id)
    except Project.DoesNotExist:
        request.session['error'] = 'The project does not exist.'
        return redirect('index')
    
    context = {'project': proj}
    return render(request, 'main/project/classifier.html', RequestContext(request, context)) 

def docs_view(request):
    file_path = os.path.join(ROOT_DIR, '..', 'readme.html')    
    file = open(file_path, 'r')
    return HttpResponse(file.read(), mimetype="text/html")

def index(request):
    context = {}
    if 'error' in request.session:
        context['error'] = request.session['error']
        request.session.pop('error')
    if 'success' in request.session:
        context['success'] = request.session['success']
        request.session.pop('success')
    if request.user.is_authenticated():
        context['projects'] = Project.objects.filter(author=request.user) 
    return render(request, 'main/index.html', RequestContext(request, context))
