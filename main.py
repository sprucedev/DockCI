import os

from flask import Flask, render_template, request
from yaml import safe_load as yaml_load, dump as yaml_dump

app = Flask(__name__)

@app.route('/')
def root():
    return render_template('index.html', jobs=list(all_jobs()))

@app.route('/jobs/<slug>', methods=('GET', 'POST'))
def job(slug):
    job = Job(slug)

    if request.method == 'POST':
        for att in ('name', 'repo'):
            setattr(job, att, request.form[att])

        job.save()

    return render_template('job.html', job=job)

@app.route('/jobs/<slug>/edit', methods=('GET',))
def job_edit(slug):
    return render_template('job_edit.html', job=Job(slug))

class YamlModelMeta(type):
    """
    Metaclass for replacing OnAccess and child classes in fields with their
    associated caching behaviour
    """
    def __new__(cls, f_clsname, f_bases, f_attrs):
        f_cls = (f_clsname, f_bases, f_attrs)
        for name, val in list(f_attrs.items()):
            if isinstance(val, YamlModelMeta.OnAccess):
                val.var_name = name
                val.future_cls = f_cls
                f_attrs[name] = val.property_value()

        return super(YamlModelMeta, cls).__new__(cls, f_clsname, f_bases, f_attrs)

    class OnAccess(object):
        """
        Mark a field as having a one-time call associated with it's retrieval
        """
        # TODO split out into a model package (model.OnAccess)
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
        # TODO split out into a model package (model.LoadOnAccess)
        def __init__(self, *args, **kwargs):
            def loader(self_):
                self_.load()
                return self_._lazy_vals[self.var_name]

            super(YamlModelMeta.LoadOnAccess, self).__init__(loader, *args, **kwargs)

        def property_value(self):
            prop = super(YamlModelMeta.LoadOnAccess, self).property_value()
            f_attrs = self.future_cls[2]
            lst = f_attrs.setdefault('_load_on_access', [])
            lst.append(self.var_name)
            return prop

class YamlModel(object, metaclass=YamlModelMeta):
    """
    A model-like base for the YAML data store
    """
    def __init__(self):
        # Used for LoadOnAccess
        self._lazy_vals = {}

    def _data_name(self):
        """
        Get the data name associated with this model type
        """
        return '%ss' % self.__class__.__name__.lower()

    def data_file(self):
        """
        Get the data file associated with this model object
        """
        return 'data/%s/%s.yaml' % (self._data_name(), self.slug)

    def load(self):
        """
        Fill the object from the job file
        """
        with open(self.data_file()) as fh:
            data = yaml_load(fh)
            for var_name in self._load_on_access:
                setattr(self, var_name, data.get(var_name, None))

    def save(self):
        """
        Save the job data
        """
        yaml_data = yaml_dump(self.as_dict(), default_flow_style=True)
        with open(self.data_file(), 'w') as fh:
            fh.write(yaml_data)

    def as_dict(self):
        """
        Serialize to dict
        """
        return {var_name: getattr(self, var_name, None)
                for var_name
                in self._load_on_access}

class Job(YamlModel):
    def __init__(self, slug=None):
        super(Job, self).__init__()
        self.slug = slug

    repo = YamlModelMeta.LoadOnAccess()
    name = YamlModelMeta.LoadOnAccess()

def all_jobs():
    """
    Get the list of jobs
    """
    for fn in os.listdir('data/jobs'):
        if os.path.isfile('data/jobs/%s' % fn) and fn.endswith('.yaml'):
            job = Job(fn[:-5])
            yield job

def setup_data():
    """
    Setup the data dirs for storing jobs/etc
    """
    os.makedirs('data/jobs', exist_ok=True)

if __name__ == "__main__":
    setup_data()
    app.run(debug=True)
