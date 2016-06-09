define([
    'knockout'
  , 'lodash'
  , 'app/util'
  , '../models/role'
], function (
    ko
  , _
  , util
  , RoleModel
) {
    function UserModel (params) {
        finalParams = $.extend({
              'email': null
            , 'active': null
            , 'roles': []
        }, params)

        this.email = util.param(finalParams['email'])
        this.active = util.param(finalParams['active'])
        this.roles = util.paramArray(finalParams['roles'])

        this._detail = null
        this.detail = ko.computed({
            read: function() {
              return _.isNil(this._detail) ?
                '/api/v1/users/' + this.email() :
                this._detail
            }.bind(this)
          , write: function(value) {
              this._detail = value
            }.bind(this)
          , owner: this
        })

        this.reload_from = function (data) {
            var i, roleModels = []

            if(typeof(data) === 'undefined') { return }
            finalData = $.extend({
                  'email': null
                , 'active': null
                , 'roles': []
            }, data)
            this.email(data['email'])
            this.active(data['active'])
            this.roles(RoleModel.putAll(data.roles))
        }.bind(this)

        this.forApi = function(isNew) {
            return {
                'email': this.email() || undefined
              , 'active': this.active()
              , 'roles': _.map(this.roles(), function(role) {
                  return role.name()
                })
            }
        }.bind(this)

        this.reload = function () {
            return $.ajax(this.detail(), {
                'dataType': 'json'
            }).done(function(data) {
              this.reload_from(data)
            }.bind(this))
        }.bind(this)

        this.save = function() {
            return $.ajax(this.detail(), {
                'method': 'POST'
              , 'data': JSON.stringify(this.forApi())
              , 'dataType': 'json'
              , 'contentType': 'application/json'
            })
        }.bind(this)

        this.delete = function() {
            return $.ajax(this.detail(), {
                'method': 'DELETE'
              , 'dataType': 'json'
            })
        }.bind(this)
    }
    return UserModel
})
