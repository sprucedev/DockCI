from flask_restful import Resource

from .util import clean_attrs, set_attrs

class BaseDetailResource(Resource):
    def handle_write(self, model, parser):
        args = parser.parse_args(strict=True)
        args = clean_attrs(args)
        set_attrs(model, args)
        DB.session.add(model)
        DB.session.commit()
        return model
