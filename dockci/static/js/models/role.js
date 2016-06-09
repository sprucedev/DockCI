define(['knockout', 'lodash', 'app/util'], function (ko, _, util) {
  function RoleModel (params) {
    finalParams = $.extend({
        'name': null
      , 'description': null
    }, params)

    this.name = util.param(finalParams['name'])
    this.description = util.param(finalParams['description'])

    this.reload_from = function (data) {
      if(typeof(data) === 'undefined') { return }
      finalData = $.extend({
          'name': null
        , 'description': null
      }, data)
      this.name(data['name'])
      this.description(data['description'])
    }.bind(this)
  }

  RoleModel._singletons = {}
  RoleModel.all = ko.observableArray()

  RoleModel.allCompletions = ko.computed(function() {
    return _.map(RoleModel.all(), function(role) {
      return [role.name(), role.description()]
    })
  })

  RoleModel.get = function(name) {
    var model = RoleModel._singletons[name]
    if (typeof(model) === 'undefined') { return null }
    return model
  }
  RoleModel.put = function(data) {
    var model = RoleModel.get(data.name)
    if (model === null) {
      model = new RoleModel(data)
      RoleModel._singletons[data.name] = model
      RoleModel.all.push(model)
    } else {
      model.reload_from(data)
    }
    return model
  }
  RoleModel.putAll = function(dataArr) {
    var i, retArr = []
    for (var i = 0; i < dataArr.length; i++) {
      retArr.push(RoleModel.put(dataArr[i]))
    }
    return retArr
  }

  RoleModel.reloadAll = function() {
    return $.ajax('/api/v1/roles', {
        'dataType': 'json'
    }).done(function(data) {
      this.putAll(data)
    }.bind(this))
  }

  return RoleModel
})
