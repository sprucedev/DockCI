from datetime import datetime

import jwt

from flask import url_for
from flask_restful import fields, Resource
from flask_security import current_user, login_required

from . import DT_FORMATTER
from .base import BaseRequestParser
from .exceptions import OnlyMeError, WrappedTokenError, WrongAuthMethodError
from .fields import NonBlankInput
from dockci.server import API, CONFIG


JWT_ME_DETAIL_PARSER = BaseRequestParser()

JWT_NEW_PARSER = BaseRequestParser()
JWT_NEW_PARSER.add_argument('name',
                            required=True, type=NonBlankInput(),
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
            raise OnlyMeError("create JWT tokens")

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


class JwtMeDetail(Resource):
    @login_required
    def get(self):
        args = JWT_ME_DETAIL_PARSER.parse_args()
        if args['api_key'] is None:
            raise WrongAuthMethodError("a JWT token")
        else:
            return JwtDetail().get(args['api_key'])

    @login_required
    def post(self):
        return JwtNew().post(current_user.id)


class JwtDetail(Resource):
    def get(self, token):
        try:
            jwt_data = jwt.decode(token, CONFIG.secret)

        except jwt.exceptions.InvalidTokenError as ex:
            raise WrappedTokenError(ex)

        jwt_data['iat'] = DT_FORMATTER.format(
            datetime.fromtimestamp(jwt_data['iat'])
        )

        try:
            user_id = jwt_data['sub']
            jwt_data['sub_detail'] = url_for('user_detail', user_id=user_id)
        except KeyError:
            pass

        return jwt_data


API.add_resource(JwtNew,
                 '/users/<int:id>/jwt',
                 endpoint='jwt_user_new')
API.add_resource(JwtMeDetail,
                 '/me/jwt',
                 endpoint='jwt_me_detail')
API.add_resource(JwtDetail,
                 '/jwt/<string:token>',
                 endpoint='jwt_detail')
