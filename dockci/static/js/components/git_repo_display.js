define([
      'knockout'
    , '../util'
    , 'text!./git_repo_display.html'
], function(ko, util, template) {
    function GitRepoDisplayModel(params) {
        this.display_repo = util.param(params['display_repo'])

        this.display_repo_uri = ko.computed(function() {
            return URI(this.display_repo())
        }.bind(this))

        this.is_github = ko.computed(function() {
            return this.display_repo_uri().hostname() === 'github.com'
        }.bind(this))
        this.bare_repo_name = ko.computed(function() {
            if (this.is_github()) {
                repo_path = this.display_repo_uri().path()
                if (repo_path.startsWith('/')) {
                    repo_path = repo_path.substr(1)
                }
                if (repo_path.endsWith('.git')) {
                    repo_path = repo_path.substr(0, repo_path.length - 4)
                }
                return repo_path
            } else {
                return this.display_repo()
            }
        }.bind(this))

        this._all_details = ko.computed(function() {
            var bare_repo_name = this.bare_repo_name()

            if (this.is_github()) {
                return {
                      'text': bare_repo_name
                    , 'link': 'https://github.com/' + bare_repo_name
                    , 'icon': '/static/img/octocat.svg'
                }
            } else {
                return {
                      'text': bare_repo_name
                    , 'link': null
                    , 'icon': null
                }
            }
        }.bind(this))

        this.text = ko.computed(function() { return this._all_details()['text'] }.bind(this))
        this.link = ko.computed(function() { return this._all_details()['link'] }.bind(this))
        this.icon = ko.computed(function() { return this._all_details()['icon'] }.bind(this))
    }

    ko.components.register('git-repo', {
        viewModel: GitRepoDisplayModel, template: template,
    })

    return GitRepoDisplayModel
})
