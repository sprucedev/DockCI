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
            , 'pageSize': 20
            , 'reload': false
            , 'trigReload': undefined
            , 'ready': (function(){})
        }, params)

        this.pageSize = finalParams['pageSize']

        this.messages = ko.observableArray()
        this.repos = ko.observableArray()
        this.loading = ko.observable(false)

        this.currentAccount = ko.observable()
        this.accounts = ko.computed(function() {
            var currentAccountStr = this.currentAccount(),
                list = $.unique(this.repos().map(function(repo) {
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

        loadFrom = function(page) {
            this.loading(true)
            $.ajax("/github/projects.json",  {
                  'dataType': 'json'
                , 'data': {
                      'page_size': this.pageSize
                    , 'page': page
                }
            }).done(function(reposData) {
                $(reposData['repos']).each(function(idx, repoData) {
                    this.repos.push(new GithubRepoModel({
                          'fullId': repoData['full_name']
                        , 'cloneUrl': repoData['clone_url']
                    }))
                }.bind(this))

                if(reposData['repos'].length >= this.pageSize) {
                    loadFrom(page + 1)
                } else {
                    this.loading(false)
                }
            }.bind(this)).fail(function(jqXHR, textStatus, errorThrown) {
                this.loading(false)
                util.ajax_fail(self.messages)(jqXHR, textStatus, errorThrown)
            })
        }.bind(this)

        this.clickHandler = function(repo) {
            this.action(repo)
        }.bind(this)
        this.reload = function() {
            this.repos([])
            loadFrom(1)
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
