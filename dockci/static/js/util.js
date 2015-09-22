dockci.ajax_fail = function(messages_ob) {
    return function (jqXHR, textStatus, errorThrown) {
        var message = (jqXHR.responseJSON || {})['message'] || textStatus
        messages_ob([
            new dockci.MessageModel({'message': message, 'category': 'danger'})
        ])
    }
}
