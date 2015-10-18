define(['jquery', 'knockout'], function ($, ko) {
    function ProjectModel(params) {
        this.slug = ko.observable()
        this.name = ko.observable()
        this.repo = ko.observable()
        this.utility = ko.observable()

        this.github_repo_id = ko.observable()

        this.hipchat_room = ko.observable()
        this.hipchat_api_token = ko.observable()

        this.link = ko.computed(function() {
            return '/projects/' + this.slug()
        }.bind(this))
        this.type_text = ko.computed(function() {
            return this.utility() ? 'utility' : 'project'
        }.bind(this))
        this.forApi = function(isNew) {
            var baseParams = {
                'name': this.name() || '',
                'repo': this.repo() || '',
                'hipchat_room': this.hipchat_room() || undefined,
                'hipchat_api_token': this.hipchat_api_token() || undefined,
            }
            if(isNew) {
                return $.extend(baseParams, {
                    'utility': this.utility(),
                    'github_repo_id': this.github_repo_id() || undefined,
                })
            } else {
                return baseParams
            }
        }.bind(this)

        this.reload_from = function (data) {
            if(typeof(data) === 'undefined') { return }
            finalData = $.extend({
                  'slug': ''
                , 'name': ''
                , 'repo': ''
                , 'utility': false
                , 'github_repo_id': ''
                , 'hipchat_room': ''
            }, data)
            this.slug(data['slug'])
            this.name(data['name'])
            this.repo(data['repo'])
            this.utility(data['utility'])
            this.github_repo_id(data['github_repo_id'])
            this.hipchat_room(data['hipchat_room'])
        }.bind(this)

        this.reload = function () {
            return $.ajax("/api/v1/projects/" + this.slug(), {
                  'dataType': 'json'
            }).done(function(data) {
                this.reload_from(data)
            }.bind(this))
        }.bind(this)

        this.save = function(isNew) {
            return $.ajax("/api/v1/projects/" + this.slug(), {
                  'method': isNew === true ? 'PUT' : 'POST'
                , 'data': this.forApi(isNew)
                , 'dataType': 'json'
            })
        }.bind(this)

        this.delete = function() {
            return $.ajax("/api/v1/projects/" + this.slug(), {
                  'method': 'DELETE'
                , 'dataType': 'json'
            })
        }.bind(this)

        this.queueJob = function(commitRef) {
            return $.ajax("/api/v1/projects/" + this.slug() + '/jobs', {
                  'method': 'POST'
                , 'data': {'commit': commitRef}
                , 'dataType': 'json'
            })
        }.bind(this)

        this.reload_from(params)
    }

    return ProjectModel
})