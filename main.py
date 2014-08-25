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

def load_on_access(var_name):
    """
    Property that tries to call .load if the value is not set
    """
    def getter(self):
        try:
            value = getattr(self, var_name)
        except AttributeError:
            self.load()
            value = getattr(self, var_name)
        return value

    def setter(self, value):
        return setattr(self, var_name, value)

    return property(getter, setter, None)

class Job(object):
    def __init__(self, slug=None):
        self.slug = slug

    repo = load_on_access('_repo')
    name = load_on_access('_name')

    def load(self):
        """
        Fill the object from the job file
        """
        with open('data/jobs/%s.yaml' % self.slug) as fh:
            data = yaml_load(fh)
            self.repo = data.get('repo', None)
            self.name = data.get('name', self.slug)

    def save(self):
        """
        Save the job data
        """
        yaml_data = yaml_dump(self.as_dict(), default_flow_style=True)
        with open('data/jobs/%s.yaml' % self.slug, 'w') as fh:
            fh.write(yaml_data)

    def as_dict(self):
        """
        Serialize to dict
        """
        return {att: getattr(self, att) for att in ('name', 'repo')}

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
