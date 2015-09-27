define([
      'knockout'
    , './models/message'
], function (ko, MessageModel) {
    util = {}
    util.ajax_fail = function(messages_ob) {
        return function (jqXHR, textStatus, errorThrown) {
            var message = (jqXHR.responseJSON || {})['message'] || textStatus
            messages_ob([
                new MessageModel({'message': message, 'category': 'danger'})
            ])
        }
    }
    util.param = function(value, def, obsType) {
        return typeof(value) === 'function' ? value : util._paramObs(value, def, obsType)
    }
    util.paramArray = function(value, def) {
        return util.param(value, def, ko.observableArray)
    }
    util._paramObs = function(value, def, obsType) {
        obsType = typeof(obsType) === 'undefined' ? ko.observable : obsType
        return obsType(
            typeof(value) !== 'undefined' ? value : util._paramDef(def)
        )
    }
    util._paramDef = function(def) {
        return typeof(def) === 'function' ? def() : def
    }
    return util
})
