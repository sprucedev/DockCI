define([
    'knockout'
  , '../util'
  , '../models/user'
  , 'text!./config_users.html'

  , 'app/components/config_user_row'
  , 'app/components/loading_bar'
], function(ko, util, UserModel, template) {
  function ConfigPageUsersModel(params) {
    finalParams = $.extend({
    }, params)

    this.pageModel = params['pageModel']
    this.users = ko.observableArray()

    this.loading = ko.observable(false)

    this.reload = function() {
      this.loading(true)
      $.ajax("/api/v1/users").done(function(usersListData) {
        this.users([])
        $(usersListData).each(function(idx, userData) {
          this.users.push(new UserModel(userData))
        }.bind(this))
      }.bind(this)).fail(function(jqXHR, textStatus, errorThrown) {
        util.ajax_fail(this.pageModel.messages)(jqXHR, textStatus, errorThrown)
      }.bind(this)).always(function() {
        this.loading(false)
      }.bind(this))
    }.bind(this)

    this.reload()
  }

  ko.components.register('config-page-users', {
    viewModel: ConfigPageUsersModel, template: template
  })

  return ConfigPageUsersModel
})
