define(['knockout', 'app/util'], function (ko, util) {
  function RegistryModel (params) {
    finalParams = $.extend({
        'display_name': null
      , 'base_name': null
      , 'username': null
      , 'password': null
      , 'email': null
      , 'insecure': false
      , 'detail': null
    }, params)

    this.display_name = util.param(finalParams['display_name'])
    this.base_name = util.param(finalParams['base_name'])
    this.username = util.param(finalParams['username'])
    this.password = util.param(finalParams['password'])
    this.email = util.param(finalParams['email'])
    this.insecure = util.param(finalParams['insecure'])
    this.raw_detail = util.param(finalParams['detail'])

    this.displayText = ko.computed(function() {
      return this.display_name() + ' (' + this.base_name() + ')'
    }.bind(this))

    this.isNew = ko.computed(function() { return this.raw_detail() === null }.bind(this))

    this.detail = ko.computed(function() {
      var raw_detail = this.raw_detail()
      return raw_detail !== null ?
        raw_detail :
        '/api/v1/registries/' + encodeURIComponent(this.base_name())
    }.bind(this))

    this.forApi = function() {
      return {
          'display_name': this.display_name() || undefined
        , 'username': this.username() || undefined
        , 'password': this.password() || undefined
        , 'email': this.email() || undefined
        , 'insecure': this.insecure()
      }
    }.bind(this)

    this.save = function() {
      return $.ajax(this.detail(), {
          'method': this.isNew() ? 'PUT' : 'POST'
        , 'data': this.forApi()
        , 'dataType': 'json'
      })
    }.bind(this)
    this.remove = function() {
      return $.ajax(this.detail(), {'method': 'DELETE'})
    }.bind(this)
  }
  return RegistryModel
})
