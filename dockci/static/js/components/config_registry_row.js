define([
    'knockout'
  , '../util'
  , 'text!./config_registry_row.html'
], function(ko, util, template) {
  function ConfigRegistryRowModel(params) {
    finalParams = $.extend({
      'editMode': false
    }, params)

    this.saving = ko.observable(false)

    this.registry = util.param(finalParams['registry'])
    this.editMode = util.param(finalParams['editMode'])

    this.save = function() {
      this.saving(true)
      setTimeout(function() { this.saving(false) }.bind(this), 1000)
    }.bind(this)
    this.remove = function() {
      this.saving(true)
      setTimeout(function() { this.saving(false) }.bind(this), 1000)
    }.bind(this)
  }

  ko.components.register('config-registry-row', {
    viewModel: ConfigRegistryRowModel, template: template
  })

  return ConfigRegistryRowModel
})
