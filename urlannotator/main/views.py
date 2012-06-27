from django.shortcuts import render, redirect
from urlannotator.main.forms import NewUserForm, UserLoginForm
from django.contrib.auth.models import User
from urlannotator.main.models import UserProfile
from django.template import RequestContext, Context
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.template.loader import get_template
import hashlib

def pass_recover(request):
    return render(request, 'main/index.html')

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
        key = hashlib.sha1()
        key.update('%s%s%s' % ('thereisn', form.cleaned_data['email'], 'ospoon'))
        user.get_profile().activation_key = key.hexdigest()
        user.get_profile().save()
        cont = Context({'key': key.hexdigest()})
        send_mail(subjectTemplate.render(cont).replace('\n', ''), bodyTemplate.render(cont), 'test', ['1kroolik1@gmail.com'])
        return redirect('index')

      return render(request, 'main/register.html', RequestContext(request, context))

def logout_view(request):
  logout(request)
  return redirect('index')

def activation_view(request, key):
  prof = UserProfile.objects.filter(activation_key=key)
  if not prof:
    context = {'error': 'Wrong activation key.'}
    return render(request, 'main/index.html', RequestContext(request, context))
  else:
    prof[0].user.is_active = True
    prof[0].user.save()
    prof[0].activation_key = 'activated'
    prof[0].save()
    context = {'success': 'Your account has been activated.'}
    return render(request, 'main/index.html', RequestContext(request, context))
  return redirect('index')

@csrf_protect
def login_view(request):
  if request.method == "GET":
    return render(request, 'main/index.html')
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
        
def facebook_login(request):
  return redirect('index')
  
def gplus_login(request):
  return redirect('index')

def twitter_login(request):
  return redirect('index')

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
