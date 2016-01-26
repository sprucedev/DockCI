define([
      'knockout'
    , 'md5'
    , './models/message'
], function (ko, md5, MessageModel) {
    util = {}
    util.ajax_fail = function(messages_ob) {
        return function (jqXHR, textStatus, errorThrown) {
            var message = (jqXHR.responseJSON || {})['message'] || textStatus
            if(typeof(message) === 'object') {
                // TODO use fields to add messages next to inputs
                messages_ob($.map(message, function(message){
                    return new MessageModel(
                        {'message': message, 'category': 'danger'}
                    )
                }))
            } else {
                messages_ob([new MessageModel(
                    {'message': message, 'category': 'danger'}
                )])
            }
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

    util.isEmpty = function(value) {
        return (
            typeof(value) === 'undefined' ||
            value === null ||
            value === ''
        )
    }

    util.gravatarUrl = function(email, size) {
        var hash = md5(email.trim().toLowerCase());
        return 'https://secure.gravatar.com/avatar/' + hash + '?d=mm&s=' + size
    }

    // MODIFIED FROM http://www.knockmeout.net/2011/04/pausing-notifications-in-knockoutjs.html
    //wrapper for a computed observable that can pause its subscriptions
    util.pauseableComputed = function(options) {
        var _cachedValue = "";
        var _isPaused = ko.observable(false);
        var _readFunc = options['read'];

        options['read'] = function() {
            if (!_isPaused()) {
                //call the actual function that was passed in
                return _readFunc.call(this);
            }
            return _cachedValue;
        }

        //the computed observable that we will return
        var result = ko.computed(options)

        //keep track of our current value and set the pause flag to release our actual subscriptions
        result.pause = function() {
            _cachedValue = this();
            _isPaused(true);
        }.bind(result);

        //clear the cached value and allow our computed observable to be re-evaluated
        result.resume = function() {
            _cachedValue = "";
            _isPaused(false);
        }

        return result;
    };

    return util
})
