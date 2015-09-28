define([
      'knockout'
    , '../util'
    , '../models/github_repo'
    , 'text!./github_repos_list.html'
    , './loading_bar'
], function(ko, util, GithubRepoModel, template) {
    function GithubReposListModel(params) {
        finalParams = $.extend({
              'action': (function(){})
            , 'columnSize': 4
            , 'reload': false
            , 'trigReload': undefined
            , 'ready': (function(){})
        }, params)

        this.messages = ko.observableArray()
        this.repos = ko.observableArray()
        this.loading = ko.observable(false)

        this.currentAccount = ko.observable()
        this.accounts = ko.computed(function() {
            var currentAccountStr = this.currentAccount(),
                list = $.unique(this.repos().map(function(idx, repo) {
                    return repo.fullId().split('/')[0]
                }))
            if(typeof(currentAccountStr) == 'undefined' || $.inArray(this.currentAccount(), list) === -1) {
                this.currentAccount(list[0])
            }
            return list
        }.bind(this))

        this.columnSize = util.param(finalParams['columnSize'])

        this.no_repos = ko.computed(function() {
            return (!this.loading()) && this.repos().length == 0
        }.bind(this))
        this.columnClass = ko.computed(function() {
            return "col-sm-" + this.columnSize()
        }.bind(this))

        this.action = finalParams['action']

        this.clickHandler = function(repo) {
            this.action(repo)
        }.bind(this)
        this.reload = function() {
            this.loading(true)
            $.ajax("/github/projects.json",  {'dataType': 'json'})
                .done(function(reposData) {
                    this.repos($(reposData['repos']).map(function(idx, repoData) {
                        return new GithubRepoModel({
                              'fullId': repoData['full_name']
                            , 'cloneUrl': repoData['clone_url']
                        })
                    }))
                }.bind(this))
                .always(function(){
                    this.loading(false)
                }.bind(this))
                .fail(util.ajax_fail(self.messages))
        }.bind(this)

        if(finalParams['reload']) {
            this.reload()
        }

        // TRIGGERS
        util.param(finalParams['trigReload']).subscribe(function() {
            this.reload()
        }.bind(this))
        finalParams['ready'](true)
    }

    ko.components.register('github-repos-list', {
        viewModel: GithubReposListModel, template: template,
    })

    return GithubReposListModel
})
    // function ThisPage() {
    //             var self = this

    //             self.messages = ko.observableArray()
    //             self.projects = ko.observableArray()
    //             self.utilities = ko.observableArray()

    //             self.loadingProjects = ko.observable(true)
    //             self.addVisible = ko.observable(false)
    //             self.addTitle = ko.observable()
    //             self.addBaseProject = ko.observable(new ProjectModel({}))

    //             function no_list_gen(observable) {
    //                 return ko.computed(function() {
    //                     return !self.loadingProjects() && observable().length == 0
    //                 })
    //             }

    //             self.no_projects = no_list_gen(self.projects)
    //             self.no_utilities = no_list_gen(self.utilities)

    //             self.addHandler = function(addWhat) {
    //                 self.addBaseProject(
    //                     new ProjectModel({'utility': addWhat === 'utility'})
    //                 )
    //                 self.addTitle("Add " + addWhat)
    //                 self.addVisible(true)
    //             }

    //             function ajax_always() { self.loadingProjects(false) }

    //             self.reload_projects = function() {
    //                 self.loadingProjects(true)
    //                 $.ajax("/api/v1/projects", {'dataType': 'json'})
    //                     .done(function(projects) {
    //                         var mappedProjects = $.map(projects, function(project) {
    //                             return new ProjectModel(project)
    //                         })
    //                         self.projects(mappedProjects.filter(function(project) { return ! project.utility() }))
    //                         self.utilities(mappedProjects.filter(function(project) { return project.utility() }))
    //                     })
    //                     .always(ajax_always)
    //                     .fail(util.ajax_fail(self.messages))
    //             }.bind(self)

    //             self.reload_projects()
    //         }
    //         require(['knockstrap'], function () {
    //             ko.applyBindings(new ThisPage())
    //         })
