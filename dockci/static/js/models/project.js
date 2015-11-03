define(['jquery', 'knockout', '../util'], function ($, ko, util) {
    function ProjectModel(params) {
        this.slug = ko.observable()
        this.name = ko.observable()
        this.repo = ko.observable()
        this.utility = ko.observable()

        this.gitlab_base_uri = ko.observable()
        this.gitlab_repo_id = ko.observable()
        this.gitlab_private_token = ko.observable()

        this.github_secret = ko.observable()
        this.github_repo_id = ko.observable()

        this._branchesLoaded = ko.observable()
        this._branches = ko.observableArray()
        this.branches = util.pauseableComputed({
            'read': function() {
              if(!this._branchesLoaded()) { this.reloadBranches() }
              return this._branches()
            }.bind(this)
          , 'deferEvaluation': true
        })

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
                'github_secret': this.github_secret() || undefined,
                'gitlab_private_token': this.gitlab_private_token() || undefined,
            }
            if(isNew) {
                return $.extend(baseParams, {
                    'utility': this.utility(),
                    'gitlab_base_uri': this.gitlab_base_uri() || undefined,
                    'gitlab_repo_id': this.gitlab_repo_id() || undefined,
                    'github_repo_id': this.github_repo_id() || undefined,
                })
            } else {
                return baseParams
            }
        }.bind(this)

        this.isType = function(typeString) {
            if (typeString === 'github') {
                return this.github_repo_id() != null
            } else if (typeString === 'gitlab') {
                return this.gitlab_repo_id() != null
            } else if (typeString === 'manual') {
                return this.github_repo_id() == null && this.gitlab_repo_id == null
            }
            return false
        }.bind(this)

        this.reload_from = function (data) {
            if(typeof(data) === 'undefined') { return }
            finalData = $.extend({
                  'slug': ''
                , 'name': ''
                , 'repo': ''
                , 'utility': false
                , 'gitlab_base_uri': ''
                , 'gitlab_repo_id': ''
                , 'github_repo_id': ''
            }, data)
            this.slug(data['slug'])
            this.name(data['name'])
            this.repo(data['repo'])
            this.utility(data['utility'])
            this.gitlab_base_uri(data['gitlab_base_uri'])
            this.gitlab_repo_id(data['gitlab_repo_id'])
            this.github_repo_id(data['github_repo_id'])
        }.bind(this)

        this.reload = function () {
            return $.ajax("/api/v1/projects/" + this.slug(), {
                  'dataType': 'json'
            }).done(function(data) {
                this.reload_from(data)
            }.bind(this))
        }.bind(this)
        this.reloadBranches = function () {
            return $.ajax("/api/v1/projects/" + this.slug() + "/branches", {
                'dataType': 'json'
            }).done(function(data) {
                this.branches.pause()
                this._branchesLoaded(true)
                this._branches(data)
                this.branches.resume()
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
