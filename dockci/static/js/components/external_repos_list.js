define([
      'knockout'
    , '../util'
    , '../models/github_repo'
    , '../models/gitlab_repo'
    , 'text!./external_repos_list.html'
    , './loading_bar'
], function(ko, util, GithubRepoModel, GitlabRepoModel, template) {
    function ExternalReposListModel(params) {
        finalParams = $.extend({
              'action': (function(){})
            , 'columnSize': 4
            , 'pageSize': 20
            , 'reload': false
            , 'trigReload': undefined
            , 'cancelReload': undefined
            , 'ready': (function(){})
            , 'redirect': ko.observable()
            , 'repoSource': 'github'
        }, params)

        this.pageSize = finalParams['pageSize']
        this.repoSource = finalParams['repoSource']

        this.messages = ko.observableArray()
        this.repos = ko.observableArray()
        this.loading = ko.observable(false)

        this.currentAccount = ko.observable()
        this.accounts = ko.computed(function() {
            var currentAccountStr = this.currentAccount(),
                list = $.unique(this.repos().map(function(repo) {
                    return repo.account()
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
        this.redirect = finalParams['redirect']

        this.loadFrom = function(page) {
            this.loading(true)
            this.loading($.ajax("/" + this.repoSource + "/projects.json",  {
                  'dataType': 'json'
                , 'data': {
                      'per_page': this.pageSize
                    , 'page': page
                }
            }).done(function(reposData) {
                if(typeof(reposData) == 'object' && 'redirect' in reposData) {
                    this.redirect(reposData['redirect'])
                    return
                }

                $(reposData['repos']).each(function(idx, repoData) {
                    if(this.repoSource === 'github') {
                        this.repos.push(new GithubRepoModel({
                              'fullId': repoData['full_name']
                            , 'cloneUrl': repoData['clone_url']
                        }))
                    } else {
                        this.repos.push(new GitlabRepoModel({
                              'fullId': repoData['path_with_namespace']
                            , 'cloneUrl': repoData['http_url_to_repo']
                        }))
                    }
                }.bind(this))

                if(reposData['repos'].length >= this.pageSize) {
                    this.loadFrom(page + 1)
                } else {
                    this.loading(false)
                }
            }.bind(this)).fail(function(jqXHR, textStatus, errorThrown) {
                this.loading(false)
                util.ajax_fail(this.messages)(jqXHR, textStatus, errorThrown)
            }.bind(this)))
        }.bind(this)

        this.clickHandler = function(repo) {
            this.action(repo)
        }.bind(this)
        this.reload = function() {
            this.repos([])
            this.loadFrom(1)
        }.bind(this)

        if(finalParams['reload']) {
            this.reload()
        }

        // TRIGGERS
        util.param(finalParams['trigReload']).subscribe(function() {
            this.reload()
        }.bind(this))
        util.param(finalParams['cancelReload']).subscribe(function() {
            loading = this.loading()
            if(loading) {
                loading.abort()
                this.loading(false)
            }
        }.bind(this))
        finalParams['ready'](true)
    }

    ko.components.register('external-repos-list', {
        viewModel: ExternalReposListModel, template: template,
    })

    return ExternalReposListModel
})
