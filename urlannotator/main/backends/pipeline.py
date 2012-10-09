from django.contrib.auth.models import User


def create_user(request, user, details, *args, **kwargs):
    """
        Inserted into django_social_auth pipeline to differentiate social
        register requests from login requests.
    """
    # If user already exists, don't create a user.
    if user is not None:
        return None

    is_new = False
    user = None

    username = details['username']
    email = details.get('email') or username
    user = User.objects.create_user(username=username, email=email,
        password='!')
    is_new = True

    return {
        'user': user,
        'is_new': is_new
    }
