define([
    'knockout'
  , '../util'
  , '../models/message'
  , '../models/role'
  , '../models/user'
  , 'text!./config_user_row.html'

  , 'app/components/loading_bar'
  , 'app/components/tag_pill'
  , 'app/components/text_input_completion'
], function(ko, util, MessageModel, RoleModel, UserModel, template) {
  function ConfigUserRowModel(params) {
    finalParams = $.extend({
        'editMode': false
      , 'messages': []
      , 'userList': []
    }, params)

    this.roleCompletions = RoleModel.allCompletions

    this.saving = ko.observable(false)
    this.loading = ko.observable(false)
    this.messages = util.paramArray(finalParams['messages'])
    this.userList = util.paramArray(finalParams['userList'])

    this.user = util.param(finalParams['user'])
    this._origEmail = ko.observable(this.user().email())
    this.editMode = util.param(finalParams['editMode'])

    this.savable = ko.computed(function() {
      var email = this.user().email()
      return email !== null && email.length >= 3 && email.indexOf('@') >= 0
    }.bind(this))

    this.roleAddValue = ko.observable('')
    this.roleAddClick = function(value) {
      var user = this.user(), role = RoleModel.get(value)
      user.roles.push(role)
      this.roleAddValue('')
    }.bind(this)
    this.roleRemoveClick = function(role) {
      var user = this.user()
      user.roles.remove(role)
    }.bind(this)

    this.editToggle = function() {
      this.edit(!this.editMode())
    }.bind(this)
    this.edit = function(setTo) {
      var user = this.user()

      this.editMode(setTo)
      user.email(this._origEmail())

      if (setTo) {
        this.reload()
        RoleModel.reloadAll()
        user.detail(user.detail())  // fixed detail URL to save email changes
      } else {
        user.detail(null)  // generated detail URL
      }
    }.bind(this)
    this.reload = function() {
      this.loading(true)
      this.user().reload().always(function() {
        this.loading(false)
      }.bind(this)).fail(function(jqXHR, textStatus, errorThrown) {
        this.editMode(false)
        util.ajax_fail(this.messages)(jqXHR, textStatus, errorThrown)
      }.bind(this))
    }.bind(this)
    this.saveHandler = function() {
      this.save('saved')
    }.bind(this)
    this.save = function(action) {
      var user = this.user()
      this.saving(true)
      user.save().success(function() {
        this.messages([new MessageModel({
            'message': "User " + user.email() + " " + action
          , 'category': 'success'
        })])
        this.edit(false)
      }.bind(this)).always(function() {
        this.saving(false)
      }.bind(this)).fail(util.ajax_fail(this.messages))
    }.bind(this)
    this.userActiveToggle = function() {
      var user = this.user(), active = user.active()
      this.user().active(!active)
      this.save(active ? 'disabled' : 'enabled')
    }.bind(this)
  }

  ko.components.register('config-user-row', {
    viewModel: ConfigUserRowModel, template: template
  })

  return ConfigUserRowModel
})
