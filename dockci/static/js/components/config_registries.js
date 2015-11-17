define([
    'knockout'
  , '../util'
  , '../models/registry'
  , 'text!./config_registries.html'

  , 'app/components/config_registry_row'
  , 'app/components/loading_bar'
], function(ko, util, RegistryModel, template) {
  function ConfigPageRegistriesModel(params) {
    finalParams = $.extend({
    }, params)

    this.pageModel = params['pageModel']
    this.registries = ko.observableArray()
    this.newRegistry = ko.observable(new RegistryModel({}))

    this.loading = ko.observable(false)

    this.reload = function() {
      this.loading(true)
      $.ajax("/api/v1/registries").done(function(regListData) {
        this.registries([])
        $(regListData).each(function(idx, regData) {
          this.registries.push(new RegistryModel(regData))
        }.bind(this))
      }.bind(this)).fail(function(jqXHR, textStatus, errorThrown) {
        util.ajax_fail(this.pageModel.messages)(jqXHR, textStatus, errorThrown)
      }.bind(this)).always(function() {
        this.loading(false)
      }.bind(this))
    }.bind(this)

    this.reload()
  }

  ko.components.register('config-page-registries', {
    viewModel: ConfigPageRegistriesModel, template: template
  })

  return ConfigPageRegistriesModel
})
