define(['knockout', 'app/util'], function (ko, util) {
  function RegistryModel (params) {
    finalParams = $.extend({
        'display_name': null
      , 'base_name': null
      , 'username': null
      , 'password': null
      , 'email': null
      , 'detail': null
    }, params)

    this.display_name = util.param(finalParams['display_name'])
    this.base_name = util.param(finalParams['base_name'])
    this.username = util.param(finalParams['username'])
    this.password = util.param(finalParams['password'])
    this.email = util.param(finalParams['email'])
    this.detail = util.params(finalParams['detail'])
  }
  return RegistryModel
})
