define(['jquery', 'knockout', '../util', '../job_bus'], function ($, ko, util, job_bus) {
    function JobModel(params) {
        this.slug                = ko.observable()
        this.project_slug        = ko.observable()

        this.job_stage_slugs     = ko.observableArray()

        this.create_ts           = ko.observable()
        this.start_ts            = ko.observable()
        this.complete_ts         = ko.observable()

        this.display_repo        = ko.observable()
        this.commit              = ko.observable()
        this.git_branch          = ko.observable()
        this.tag                 = ko.observable()

        this.git_changes         = ko.observable()
        this.git_author_email    = ko.observable()
        this.git_author_name     = ko.observable()
        this.git_committer_email = ko.observable()
        this.git_committer_name  = ko.observable()

        this.docker_client_host  = ko.observable()
        this.image_id            = ko.observable()
        this.container_id        = ko.observable()

        this.exit_code           = ko.observable()
        this.result              = ko.observable()

        this.state = ko.computed(function() {
            return this.result()  // TODO running, etc
        }.bind(this))

        this.git_author_email_display = ko.computed(function() {
            return util.isEmpty(this.git_author_email()) ?
                this.git_committer_email() :
                this.git_author_email()
        }.bind(this))
        this.git_author_name_display = ko.computed(function() {
            return util.isEmpty(this.git_author_name()) ?
                this.git_committer_name() :
                this.git_author_name()
        }.bind(this))

        this.show_author = ko.computed(function() {
            return (
                !util.isEmpty(this.git_author_email_display()) &&
                !util.isEmpty(this.git_author_name_display())
            )
        }.bind(this))
        this.show_committer = ko.computed(function() {
            return (
                this.git_author_email() != this.git_committer_email() &&
                this.git_author_name() != this.git_committer_name() &&
                !util.isEmpty(this.git_committer_name()) &&
                !util.isEmpty(this.git_committer_email())
            )
        }.bind(this))

        this.bus = ko.observable()

        function stageFromSourceQueue(source_queue) {
            parts = source_queue.split('.')
            return parts[parts.length - 2]
        }

        // Update stage slugs based on live data
        this.bus.subscribe(function(new_bus) {
            new_bus.subscribe(function(message) {
                stage_slug = stageFromSourceQueue(message.headers.destination)
                if (this.job_stage_slugs.indexOf(stage_slug) === -1) {
                    this.job_stage_slugs.push(stage_slug)
                }
            }.bind(this))
        }.bind(this))

        this._liveLoadDetail = null
        this.getLiveLoadDetail = function(callback) {
            if (this._liveLoadDetail === null) {
                // TODO POST
                return $.ajax(
                    (
                        '/api/v1' +
                        '/projects/' + this.project_slug() +
                        '/jobs/' + this.slug() +
                        '/stream'
                    ), {
                        'dataType': 'json'
                    }
                ).done(function(data) {
                    this._liveLoadDetail = data
                    callback(data)
                }.bind(this))
            } else {
                callback(this._liveLoadDetail)
            }
        }.bind(this)
        this.getLiveQueueName = function(callback) {
            this.getLiveLoadDetail(function(data) {
                callback(data['live_queue'])
            })
        }.bind(this)

        this.reload_from = function (data) {
            if(typeof(data) === 'undefined') { return }
            finalData = $.extend({
                  'slug': ''
                , 'project_slug': ''

                , 'job_stage_slugs': []

                , 'create_ts': null
                , 'start_ts': null
                , 'complete_ts': null

                , 'display_repo': ''
                , 'commit': ''
                , 'branch': ''
                , 'tag': ''

                , 'git_changes': ''
                , 'git_author_email': ''
                , 'git_author_name': ''
                , 'git_committer_email': ''
                , 'git_committer_name': ''

                , 'docker_client_host': ''
                , 'image_id': null
                , 'container_id': null

                , 'exit_code': null
                , 'result': null
            }, data)
            this.slug(data['slug'])
            this.project_slug(data['project_slug'])

            this.job_stage_slugs(data['job_stage_slugs'])

            this.create_ts(data['create_ts'])
            this.start_ts(data['start_ts'])
            this.complete_ts(data['complete_ts'])

            this.display_repo(data['display_repo'])
            this.commit(data['commit'])
            this.git_branch(data['git_branch'])
            this.tag(data['tag'])

            this.git_changes(data['git_changes'])
            this.git_author_email(data['git_author_email'])
            this.git_author_name(data['git_author_name'])
            this.git_committer_email(data['git_committer_email'])
            this.git_committer_name(data['git_committer_name'])

            this.docker_client_host(data['docker_client_host'])
            this.image_id(data['image_id'])
            this.container_id(data['container_id'])

            this.exit_code(data['exit_code'])
            this.result(data['result'])

            if (util.isEmpty(this.bus())) {
                this.bus(job_bus.get(this))
            }
        }.bind(this)

        this.reload = function () {
            return $.ajax(
                (
                    '/projects/' + this.project_slug() +
                    '/jobs/' + this.slug() + '.json'
                ), {
                    'dataType': 'json'
                }
            ).done(function(data) {
                this.reload_from(data)
            }.bind(this))
        }.bind(this)

        this.reload_from(params)
    }

    JobModel.from_url = function (url, on_done) {
        return $.ajax(
            url, {'dataType': 'json'}
        ).done(function(data) {
            on_done(new JobModel(data))
        })
    }

    return JobModel
})
