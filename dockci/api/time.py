""" API relating to server time """
import datetime

from flask_restful import marshal_with, Resource

from .util import DT_FORMATTER
from dockci.server import API


NOW_FIELDS = {
    'now_ts': DT_FORMATTER,
}


class NowDetail(Resource):
    """ API to retrieve current server time """
    @marshal_with(NOW_FIELDS)
    def get(self):  # pylint:disable=no-self-use
        """ Return current server time """
        return {'now_ts': datetime.datetime.now()}


API.add_resource(NowDetail,
                 '/time/now',
                 endpoint='time_now')
