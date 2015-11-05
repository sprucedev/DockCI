"""
APIs for external information
"""
import json

from flask import request, Response

from dockci.server import APP, OAUTH_APPS
from dockci.views.oauth import oauth_required


@APP.route('/<name>/projects.json')
@oauth_required(['github', 'gitlab'])
def git_projects_list_view(name):
    """
    API for GitHub projects list
    """
    if name != 'github':
        raise NotImplementedError("Not yet!")

    data = OAUTH_APPS[name].get('user/repos', {
        'per_page': request.args.get('per_page', 18),
        'page': request.args.get('page', 1),
    }).data
    data = {'repos': [
        {
            key: value
            for key, value in repo.items()
            if key in {'full_name', 'clone_url', 'hooks_url'}
        } for repo in data
    ]}
    return Response(json.dumps(data), mimetype='application/json')


# @APP.route('/_oauth/<name>/<path:uri>')
def oauth_debug_view(name, uri):
    """
    Debugger for arbitrary OAuth GET requests
    """
    return Response(json.dumps(OAUTH_APPS[name].get(uri).data),
                    mimetype='application/json')
