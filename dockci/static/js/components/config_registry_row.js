define([
    'knockout'
  , '../util'
  , '../models/message'
  , 'text!./config_registry_row.html'
], function(ko, util, MessageModel, template) {
  function ConfigRegistryRowModel(params) {
    finalParams = $.extend({
        'editMode': false
      , 'messages': []
    }, params)

    this.saving = ko.observable(false)
    this.messages = util.paramArray(finalParams['messages'])

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
