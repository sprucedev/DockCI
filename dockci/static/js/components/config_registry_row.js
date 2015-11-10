define([
    'knockout'
  , '../util'
  , '../models/message'
  , '../models/registry'
  , 'text!./config_registry_row.html'
], function(ko, util, MessageModel, RegistryModel, template) {
  function ConfigRegistryRowModel(params) {
    finalParams = $.extend({
        'editMode': false
      , 'messages': []
      , 'regList': []
    }, params)

    this.saving = ko.observable(false)
    this.messages = util.paramArray(finalParams['messages'])
    this.regList = util.paramArray(finalParams['regList'])

    this.registry = util.param(finalParams['registry'])
    this.editMode = util.param(finalParams['editMode'])

    this.savable = ko.computed(function() {
      var   displayName = this.registry().display_name()
          , baseName = this.registry().base_name()
          , username = this.registry().username()

      return    displayName !== null && displayName !== ''
             && baseName !== null && baseName !== ''
             && username !== null && username !== ''
    }.bind(this))

    this.save = function() {
      this.saving(true)
      this.registry().save().success(function() {
        this.messages([new MessageModel({
            'message': "Registry saved"
          , 'category': 'success'
        })])
        this.regList.push(this.registry())
        this.registry(new RegistryModel({}))
      }.bind(this)).always(function() {
        this.saving(false)
      }.bind(this)).fail(util.ajax_fail(this.messages))
    }.bind(this)
    this.remove = function() {
      this.saving(true)
      this.registry().remove().success(function(data) {
        var message = "Registry deleted"
        if (typeof(data['message']) !== 'undefined') { message = data['message'] }
        this.messages([new MessageModel({
            'message': message
          , 'category': 'success'
        })])
        this.regList.remove(this.registry())
      }.bind(this)).always(function() {
        this.saving(false)
      }.bind(this)).fail(util.ajax_fail(this.messages))
    }.bind(this)
  }

  ko.components.register('config-registry-row', {
    viewModel: ConfigRegistryRowModel, template: template
  })

  return ConfigRegistryRowModel
})
