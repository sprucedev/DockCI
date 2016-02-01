"""
OAuth related API views and routes
"""

import json

from functools import wraps
from urllib.parse import urlencode

from flask import abort, flash, redirect, request, Response, url_for
from flask_login import login_user
from flask_security import current_user, login_required

from dockci.models.auth import OAuthToken, User
from dockci.server import APP, DB, OAUTH_APPS, OAUTH_APPS_SCOPE_SERIALIZERS
from dockci.util import ext_url_for, get_token_for


@APP.route('/oauth-authorized/<name>')
def oauth_authorized(name):
    """
    Callback for oauth authorizations. Handles adding the token to the logged
    in user, errors, as well as redirecting back to the original page
    """
    try:
        resp = OAUTH_APPS[name].authorized_response()

    except KeyError:
        return 404, "%s auth not available" % name

    if resp is None or 'error' in resp:
        flash("{name}: {message}".format(
            name=name.title(),
            message=request.args['error_description'],
        ), 'danger')

    else:
        if current_user.is_authenticated():
            current_user.oauth_tokens.filter_by(service=name).delete(
                synchronize_session=False,
            )
            user = current_user
            oauth_token = create_oauth_token(name, response)

        else:
            user, oauth_token = user_from_oauth(name, resp)

        user.oauth_tokens.append(oauth_token)
        DB.session.add(oauth_token)
        DB.session.add(user)
        DB.session.commit()

        flash(u"Connected to %s" % name.title(), 'success')
        login_user(user)

    try:
        return redirect(request.args['return_to'])

    except KeyError:
        return redirect(url_for('index_view'))


def create_oauth_token(name, response):
    return OAuthToken(
        service=name,
        key=response['access_token'],
        secret='',
        scope=OAUTH_APPS_SCOPE_SERIALIZERS[name](response['scope'])
    )


def user_from_oauth(name, response):
    oauth_app = OAUTH_APPS[name]
    oauth_token = create_oauth_token(name, response)
    oauth_token_tuple = (oauth_token.key, oauth_token.secret)

    if name == 'github':
        user_data = oauth_app.get('/user', token=oauth_token_tuple).data
        user_email = user_data['email']

    else:
        raise NotImplementedError("GitLab doesn't work yet")

    if User.query.filter_by(email=user_email).count() > 0:
        # If user has a <name> token already, okay
        # If user has no <name> token, can't do
        raise Exception("Already registered")  # TODO handle this

    return User(
        email=user_email,
        active=True,
    ), oauth_token


def oauth_response(oauth_app):
    return_to = request.args.get('return_to', None)
    base_url = ext_url_for(
        'oauth_authorized', name=oauth_app.name,
    )
    if return_to is not None:
        callback_uri = '{base_url}?{query}'.format(
            base_url=base_url,
            query=urlencode({'return_to': return_to})
        )

    else:
        callback_uri = base_url

    return oauth_app.authorize(callback=callback_uri)


def oauth_required(acceptable=None, force_name=None):
    """
    Wrap the view in oauth functionality to make sure there's an acceptable
    token, before moving on to the view
    """
    if force_name is not None and acceptable is not None:
        if force_name not in acceptable:
            raise ValueError(
                "Name has been forced to '%s', but this is never acceptable "
                "for set %s",
                force_name,
                acceptable,
            )

    def outer(func):
        """
        Wrap func in the inner check, and possibly force_name helper
        """
        @login_required
        @wraps(func)
        def inner_with_name(name, *args, **kwargs):
            """
            Wrap a view function to provide the redirect/return_to
            functionality on current user having no oauth
            """
            if name not in acceptable:
                return abort(404)

            oauth_app = OAUTH_APPS[name]
            if not get_token_for(oauth_app):
                resp = oauth_response(oauth_app)
                return Response(json.dumps({'redirect': resp.location}),
                                mimetype='application/json')

            else:
                if force_name is not None:
                    return func(*args, **kwargs)

                else:
                    return func(name, *args, **kwargs)

        @wraps(inner_with_name)
        def inner_forced_name(*args, **kwargs):
            """
            Wrap inner_with_name to add the name as the value given in the
            force_name param earlier
            """
            return inner_with_name(force_name, *args, **kwargs)

        if force_name is None:
            return inner_with_name

        else:
            return inner_forced_name

    return outer


@APP.route('/oauth-login/<name>')
def oauth_login(name):
    if name not in ['github', 'gitlab']:
        return abort(404)

    return oauth_response(OAUTH_APPS[name])
