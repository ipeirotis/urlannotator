from django.shortcuts import render, redirect
from urlannotator.main.forms import *
from django.contrib.auth.models import User
from urlannotator.main.models import UserProfile
from django.template import RequestContext, Context
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.template.loader import get_template
import hashlib

def pass_recover(request):
    return render(request, 'main/index.html')

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
        user = User.objects.create_user(username=form.cleaned_data['email'],email=form.cleaned_data['email'],password=form.cleaned_data['password1'])
        user.is_active = False
        user.save()
        subjectTemplate = get_template('activation_email_subject.txt')
        bodyTemplate = get_template('activation_email.txt')
        key = get_activation_key(form.cleaned_data['email'], user.get_profile().id)
        print key
        user.get_profile().activation_key = key
        user.get_profile().email_registered = True
        user.get_profile().save()
        cont = Context({'key': key})
        send_mail(subjectTemplate.render(cont).replace('\n', ''), bodyTemplate.render(cont), 'test', ['1kroolik1@gmail.com'])
        return redirect('index')

      return render(request, 'main/register.html', RequestContext(request, context))

def logout_view(request):
  logout(request)
  return redirect('index')

def activation_view(request, key):
  prof_id = key.rsplit('-', 1)
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
        if user.is_active:
          login(request,user)
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
    context['general_form'] = GeneralEmailUserForm()
    context['password_form'] = PasswordChangeForm(request.user)
  else:
    context['general_form'] = GeneralUserForm()

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
  
  if request.method == "POST":
    if 'submit' in request.POST:
      if request.POST['submit'] == 'general':
        if profile.email_registered:
          form = GeneralEmailUserForm(request.POST)
          if context['general_form'].is_valid():
            request.user.username = form.cleaned_data['full_name']
            request.user.save()
            context['success'] = 'Full name has been successfully changed.'
          else:
            context['general_form'] = form
        else:
          form = GeneralUserForm(request.POST)
          if form.is_valid():
            request.user.username = form.cleaned_data['full_name']
            request.user.save()
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
        print request.POST
        if form.is_valid():
          profile.alerts = form.cleaned_data['alerts']
          profile.save()
          context['success'] = 'Alerts setup has been successfully changed.'
        else:
          context['alerts_form'] = form
  return render(request, 'main/settings.html', RequestContext(request, context))

def odesk_login(request):
  return redirect('index')
    
def index(request):
  context = { }
  if 'error' in request.session:
    context['error'] = request.session['error']
    request.session.pop('error')
  if 'success' in request.session:
    context['success'] = request.session['success']
    request.session.pop('success')
       
  return render(request, 'main/index.html', RequestContext(request, context))
