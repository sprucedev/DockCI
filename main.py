import os

from flask import Flask, render_template, request

from yaml_model import Model, OnAccess, LoadOnAccess

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

class Job(Model):
    def __init__(self, slug=None):
        super(Job, self).__init__()
        self.slug = slug

    repo = LoadOnAccess()
    name = LoadOnAccess()

def all_jobs():
    """
    Get the list of jobs
    """
    try:
        for fn in os.listdir('data/jobs'):
            if os.path.isfile('data/jobs/%s' % fn) and fn.endswith('.yaml'):
                job = Job(fn[:-5])
                yield job

    except FileNotFoundError:
        return

if __name__ == "__main__":
    app.run(debug=True)
