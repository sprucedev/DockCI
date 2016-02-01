define(['jquery', 'knockout', '../util'], function ($, ko, util) {
    function ProjectModel(params) {
        this.slug           = ko.observable()
        this.name           = ko.observable()
        this._repo           = ko.observable()
        this.display_repo   = ko.observable()
        this.branch_pattern = ko.observable()
        this.utility        = ko.observable()

        this.forcedType = ko.observable()

        this.gitlab_base_uri      = ko.observable()
        this.gitlab_repo_id       = ko.observable()
        this.gitlab_private_token = ko.observable()

        this.github_secret  = ko.observable()
        this.github_repo_id = ko.observable()

        this.target_registry           = ko.observable()
        this._target_registry_uri      = ko.observable()
        this.target_registry_base_name = ko.computed(function() {
            target_registry = this.target_registry()
            target_registry_uri = this._target_registry_uri()

            has_target_registry = !(
                target_registry === null ||
                typeof(target_registry) === 'undefined'
            )
            has_target_registry_uri = !(
                target_registry_uri === null ||
                typeof(target_registry_uri) === 'undefined'
            )

            if(!has_target_registry && !has_target_registry_uri) {
                return target_registry
            }
            if(has_target_registry) {
                return target_registry.base_name()
            } else {
                return target_registry_uri.substr('/api/v1/registries/'.length)
            }
        }.bind(this))
        this.target_registry.subscribe(function() {
            this._target_registry_uri(undefined)
        }.bind(this))

        this._branchesLoaded = ko.observable()
        this._branches       = ko.observableArray()
        this.branches        = util.pauseableComputed({
            'read': function() {
              if(!this._branchesLoaded()) { this.reloadBranches() }
              return this._branches()
            }.bind(this)
          , 'deferEvaluation': true
        })

        this.repo = ko.computed({
            'read': function() {
                if (this._repo() === null) {
                    return ''
                } else {
                    return this._repo()
                }
            }.bind(this),
            'write': function(value) {
                if (util.isEmpty(value)) {
                    this._repo(null)
                } else {
                    this._repo(value)
                }
            }.bind(this)
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
                'repo': this._repo(),
                'branch_pattern': this.branch_pattern() || undefined,
                'github_secret': this.github_secret() || undefined,
                'gitlab_private_token': this.gitlab_private_token() || undefined,
                'target_registry': this.target_registry_base_name() || null,
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
            forcedType = this.forcedType()
            if (forcedType) { return typeString === forcedType }
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
                , 'repo': null
                , 'display_repo': ''
                , 'branch_pattern': ''
                , 'utility': false
                , 'gitlab_base_uri': ''
                , 'gitlab_repo_id': ''
                , 'github_repo_id': ''
                , 'target_registry': null
            }, data)
            this.slug(data['slug'])
            this.name(data['name'])
            this._repo(data['repo'])
            this.display_repo(data['display_repo'])
            this.branch_pattern(data['branch_pattern'])
            this.utility(data['utility'])
            this.gitlab_base_uri(data['gitlab_base_uri'])
            this.gitlab_repo_id(data['gitlab_repo_id'])
            this.github_repo_id(data['github_repo_id'])
            this._target_registry_uri(data['target_registry'])
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
