""" SQLAlchemy column types """

import re

from sqlalchemy import types

# Be very careful changing these. Changes MAY NOT be reflected in the
# migrations (eg changing ``impl`` won't correctly migrate)

class RegexType(types.TypeDecorator):
    """ Regex to unicode in, compiled regex object out """

    impl = types.Unicode

    def process_bind_param(self, value, _):
        if value is None:
            return value
        return value.pattern

    def process_result_value(self, value, _):
        if value is None:
            return value
        return re.compile(value)
