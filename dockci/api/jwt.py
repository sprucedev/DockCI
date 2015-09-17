from datetime import datetime

import jwt

from flask import request, url_for
from flask_restful import fields, inputs, marshal_with, Resource
from flask_security import current_user, login_required

from . import DT_FORMATTER
from .base import BaseDetailResource
from .util import clean_attrs, DefaultRequestParser, new_edit_parsers
from dockci.models.auth import User
from dockci.server import API, CONFIG, DB


JWT_NEW_PARSER = DefaultRequestParser(bundle_errors=True)
JWT_NEW_PARSER.add_argument('name',
                            required=True,
                            help="Service name for the token")
JWT_NEW_PARSER.add_argument('exp',
                            type=DT_FORMATTER,
                            help="Expiration time of the token")


class JwtString(fields.String):
    def format(self, value):
        return jwt.encode(value, CONFIG.secret).decode()


class JwtNew(Resource):
    @login_required
    def post(self, id):
        if current_user.id != id:
            return (
                {'message': "Can not create JWT tokens for another user"},
                401,
            )

        args = JWT_NEW_PARSER.parse_args(strict=True)
        args.update({
            'sub': id,
            'iat': datetime.utcnow(),
        })
        args = {
            key: value
            for key, value in args.items()
            if value is not None
        }

        return {'token': JwtString().format(args)}, 201


class JwtInfo(Resource):
    def get(self, token):
        try:
            jwt_data = jwt.decode(token, CONFIG.secret)

        except jwt.exceptions.InvalidTokenError as ex:
            return {'message': str(ex)}, 400

        jwt_data['iat'] = DT_FORMATTER.format(
            datetime.fromtimestamp(jwt_data['iat'])
        )

        try:
            user_id = jwt_data['sub']
            jwt_data['sub_detail'] = url_for('user_detail', id=user_id)
        except KeyError:
            pass

        return jwt_data


API.add_resource(JwtNew,
                 '/users/<int:id>/jwt',
                 endpoint='jwt_user_new')
API.add_resource(JwtInfo,
                 '/jwt/<string:token>',
                 endpoint='me_jwt_info')
