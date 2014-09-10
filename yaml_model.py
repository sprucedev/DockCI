import os

from yaml import safe_load as yaml_load, dump as yaml_dump


class OnAccess(object):
    """
    Mark a field as having a one-time call associated with it's retrieval
    """
    def __init__(self, func):
        self.func = func

    def property_value(self):
        def getter(self_):
            try:
                return self_._lazy_vals[self.var_name]
            except KeyError:
                self_._lazy_vals[self.var_name] = self.func(self_)
                return self_._lazy_vals[self.var_name]

        def setter(self_, value):
            self_._lazy_vals[self.var_name] = value

        return property(getter, setter)


class LoadOnAccess(OnAccess):
    """
    Mark a field as being lazy loaded with the _load method of the model
    class
    """
    def __init__(self, default=None, generate=None, *args, **kwargs):
        def loader(self_):
            try:
                self_.load()
                return self_._lazy_vals[self.var_name]

            except FileNotFoundError:
                if generate:
                    return generate(self) if callable(generate) else generate
                elif default:
                    return default(self) if callable(default) else default
                else:
                    raise

            except KeyError:
                if default:
                    return default(self) if callable(default) else default
                else:
                    raise

        super(LoadOnAccess, self).__init__(loader, *args, **kwargs)

    def property_value(self):
        prop = super(LoadOnAccess, self).property_value()
        f_attrs = self.future_cls[2]
        lst = f_attrs.setdefault('_load_on_access', [])
        lst.append(self.var_name)
        return prop


class ModelMeta(type):
    """
    Metaclass for replacing OnAccess and child classes in fields with their
    associated caching behaviour
    """
    def __new__(cls, f_clsname, f_bases, f_attrs):
        f_cls = (f_clsname, f_bases, f_attrs)
        for name, val in list(f_attrs.items()):
            if isinstance(val, OnAccess):
                val.var_name = name
                val.future_cls = f_cls
                f_attrs[name] = val.property_value()

        return super(ModelMeta, cls).__new__(cls, f_clsname, f_bases, f_attrs)


class Model(object, metaclass=ModelMeta):
    """
    A model-like base for the YAML data store
    """
    def __init__(self):
        # Used for LoadOnAccess
        self._lazy_vals = {}

    @classmethod
    def _data_name(cls):
        """
        Get the data name associated with this model type
        """
        return '%ss' % cls.__name__.lower()

    @classmethod
    def data_dir_path(cls):
        """
        Path parts used to create the data directory
        """
        return ['data', cls._data_name()]

    def data_file_path(self):
        """
        Path parts used to create the data filename
        """
        return self.__class__.data_dir_path() + ['%s.yaml' % self.slug]

    def load(self, data_file=None):
        """
        Fill the object from the job file
        """
        if data_file is None:
            data_file = os.path.join(*self.data_file_path())

        with open(data_file) as fh:
            data = yaml_load(fh)
            self.from_dict(data)

    def save(self, data_file=None):
        """
        Save the job data
        """
        if data_file is None:
            data_file_path = self.data_file_path()
            data_file = os.path.join(*data_file_path)

            # Make the dir first
            os.makedirs(os.path.join(*data_file_path[0:-1]), exist_ok=True)

        yaml_data = self.as_yaml()
        with open(data_file, 'w') as fh:
            fh.write(yaml_data)

    def from_yaml(self, data):
        """
        Deserialize from YAML
        """
        return self.from_dict(yaml_load(data))

    def as_yaml(self):
        """
        Serialize to YAML
        """
        return yaml_dump(self.as_dict(), default_flow_style=False)

    def from_dict(self, data):
        """
        Deserialize from dict
        """
        for var_name in self._load_on_access:
            if var_name in data:
                setattr(self, var_name, data[var_name])

    def as_dict(self):
        """
        Serialize to dict
        """
        return {var_name: getattr(self, var_name, None)
                for var_name
                in self._load_on_access}


class SingletonModel(Model):
    @property
    def slug(self):
        return self.__class__._data_name()

    @classmethod
    def data_dir_path(cls):
        return ['data']
