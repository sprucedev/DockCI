from flask_restful import fields


class RewriteUrl(fields.Url):
    """
    Extension of the Flask RESTful Url field that allows you to remap object
    fields to different names
    """
    def __init__(self,
                 endpoint=None,
                 absolute=False,
                 scheme=None,
                 rewrites=None):
        super(RewriteUrl, self).__init__(endpoint, absolute, scheme)
        self.rewrites = rewrites or {}

    def output(self, key, obj):
        data = obj.__dict__
        for field_set, field_from in self.rewrites.items():
            attr_path_data = obj
            for attr_path in field_from.split('.'):
                if attr_path_data is None:
                    return None
                attr_path_data = getattr(attr_path_data, attr_path)

            data[field_set] = attr_path_data

        return super(RewriteUrl, self).output(key, data)
