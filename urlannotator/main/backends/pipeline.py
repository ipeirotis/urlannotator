from django.contrib.auth.models import User
from django.shortcuts import redirect


def create_user(request, user, details, *args, **kwargs):
    """
        Inserted into django_social_auth pipeline to differentiate social
        register requests from login requests.
    """
    # If user already exists, don't create a user.
    if user is not None:
        return None

    email = details.get('email')
    is_new = False
    user = None

    if 'registration' in request.session:
        username = '%s-%s'\
            % (request.session['registration'], details['username'])
        user = User.objects.create_user(username=username, email=email,
            password='!')
        is_new = True
        request.session.pop('registration')
    elif user is None:
        request.session['error'] = "Account for that social media doesn't "\
            "exist. Please register first."
        return redirect('register')

    return {
        'user': user,
        'is_new': is_new
    }
