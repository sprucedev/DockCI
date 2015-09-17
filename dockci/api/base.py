from flask_restful import reqparse, Resource

from .util import clean_attrs, set_attrs


AUTH_FORM_LOCATIONS = ('form', 'headers', 'json')


class BaseDetailResource(Resource):
    def handle_write(self, model, parser):
        args = parser.parse_args(strict=True)
        args = clean_attrs(args)
        set_attrs(model, args)
        DB.session.add(model)
        DB.session.commit()
        return model


class BaseRequestParser(reqparse.RequestParser):
    def __init__(self, *args, **kwargs):
        super(BaseRequestParser, self).__init__(*args, **kwargs)
        self.add_argument('username', location=AUTH_FORM_LOCATIONS)
        self.add_argument('password', location=AUTH_FORM_LOCATIONS)
        self.add_argument('api_key', location=('args',) + AUTH_FORM_LOCATIONS)
