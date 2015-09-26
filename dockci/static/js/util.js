define(['./models/message'], function (MessageModel) {
    util = {}
    util.ajax_fail = function(messages_ob) {
        return function (jqXHR, textStatus, errorThrown) {
            var message = (jqXHR.responseJSON || {})['message'] || textStatus
            messages_ob([
                new MessageModel({'message': message, 'category': 'danger'})
            ])
        }
    }
    return util
})
