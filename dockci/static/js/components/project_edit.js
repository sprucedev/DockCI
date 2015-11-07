define([
      'knockout'
    , '../util'
    , '../models/project'

    , 'text!./project_edit.html'

    , './loading_bar'
    , './external_repos_list'
], function(ko, util, ProjectModel, template) {
    function ProjectEditModel(params) {
        finalParams = $.extend({
              'reload': false
            , 'gitlabEnabled': false
            , 'gitlabDefault': false
            , 'githubEnabled': false
            , 'githubDefault': false
            , 'isNew': true
            , 'projectData': {}
            , 'messages': []
        }, params)

        finalParams['project'] = finalParams['project'] || new ProjectModel(finalParams['project_data'])

        this.loading = ko.observable(false)

        this.messages      = util.paramArray(finalParams['messages'])
        this.project       = util.param(finalParams['project'])
        this.gitlabEnabled = finalParams['gitlabEnabled']
        this.gitlabDefault = finalParams['gitlabDefault']
        this.githubEnabled = finalParams['githubEnabled']
        this.githubDefault = finalParams['githubDefault']
        this.isNew         = util.param(finalParams['isNew'])
        this.currentTab    = util.param(finalParams['currentTab'], function() {
            if (this.gitlabDefault) { return 'gitlab' }
            if (this.githubDefault) { return 'github' }
            return 'manual'
        }.bind(this)())

        this.secretsPlaceholder = ko.computed(function(){
            return this.isNew() ? '' : '*****'
        }.bind(this))

        this.trigGithubReload = ko.observable()
        this.trigGitlabReload = ko.observable()
        this.trigCancelGithubReload = ko.observable()
        this.trigCancelGitlabReload = ko.observable()
        this.redirect = ko.observable()

        this.githubAction = function(repo) {
            this.project().repo(repo.cloneUrl())
            this.project().github_repo_id(repo.fullId())
            this.project().slug(repo.shortName())
            this.project().name(repo.shortName())
        }.bind(this)
        this.reloadGithub = function() {
            this.trigGithubReload.notifySubscribers()
        }.bind(this)
        this.cancelReloadGithub = function() {
            this.trigCancelGithubReload.notifySubscribers()
        }.bind(this)

        this.gitlabAction = function(repo) {
            this.project().repo(repo.cloneUrl())
            this.project().gitlab_repo_id(repo.fullId())
            this.project().slug(repo.shortName())
            this.project().name(repo.shortName())
        }.bind(this)
        this.reloadGitlab = function() {
            this.trigGitlabReload.notifySubscribers()
        }.bind(this)
        this.cancelReloadGitlab = function() {
            this.trigCancelGitlabReload.notifySubscribers()
        }.bind(this)

        this.currentTab.subscribe(function(val) {
            if(val === 'github') {
                this.cancelReloadGitlab()
                this.reloadGithub()
            } else if(val === 'gitlab') {
                this.cancelReloadGithub()
                this.reloadGitlab()
            }
            this.project().forcedType(val)
            this.project().gitlab_repo_id(undefined)
            this.project().github_repo_id(undefined)
        }.bind(this))

        function attachGitlabUpdates(project) {
            function updateFromGitlab() {
                baseUri = project.gitlab_base_uri()
                repoId = project.gitlab_repo_id()
                baseUriFilled = typeof(baseUri) != 'undefined' && baseUri != ''
                repoIdFilled = typeof(repoId) != 'undefined' && repoId != ''

                if (baseUriFilled && repoIdFilled) {
                    project.repo(
                        URI(baseUri + '/' + repoId + '.git')
                            .normalize()
                            .valueOf()
                    )
                }

                if (repoIdFilled && repoId.indexOf('/') != -1) {
                    project.slug(repoId.substr(repoId.indexOf('/') + 1))
                }
            }

            project.gitlab_base_uri.subscribe(updateFromGitlab)
            project.gitlab_repo_id.subscribe(updateFromGitlab)
        }
        this.project.subscribe(attachGitlabUpdates)
        attachGitlabUpdates(this.project())

        this.redirect.subscribe(function() {
            window.location.href = this.redirect()
        }.bind(this))

        if(finalParams['reload']) {
            this.loading(true)
            this.project().reload().always(function () {
                this.loading(false)
            }.bind(this))
        }
    }

    ko.components.register('project-edit', {
        viewModel: ProjectEditModel, template: template
    })

    return ProjectEditModel
})
