define([
      'knockout'
    , '../util'
    , 'text!./git_user.html'
], function(ko, util, template) {
    function GitUserModel(params) {
        this.el    = util.param(params['el'])
        this.name  = util.param(params['name'])
        this.email = util.param(params['email'])

        this.size = ko.computed(function () {
            return $(this.el()).height() + 20
        }.bind(this))
        this.gravatarUrl = ko.computed(function () {
            return util.gravatarUrl(this.email(), this.size())
        }.bind(this))
    }

    ko.components.register('git-user', {
        viewModel: GitUserModel, template: template,
    })

    return GitUserModel
})
