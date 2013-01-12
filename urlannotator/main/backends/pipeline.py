from django.contrib.auth.models import User


def create_user(request, user, details, backend, *args, **kwargs):
    """
        Inserted into django_social_auth pipeline to differentiate social
        register requests from login requests.
    """
    # If user already exists, don't create a user.
    if user is not None:
        return None

    is_new = False
    user = None

    username = '{0}-{1}'.format(details['username'], backend.name)
    email = details.get('email') or details['username']
    user = User.objects.create_user(username=username, email=email,
        password='!')
    is_new = True

    return {
        'user': user,
        'is_new': is_new
    }
