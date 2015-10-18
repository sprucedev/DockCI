define(['knockout'], function (ko) {
    function MessageModel (params) {
        finalParams = $.extend({
              'message': 'Something happened'
            , 'category': 'info'
        }, params)

        this.message = finalParams['message']
        this.category = finalParams['category']

        this.category_css = ko.computed(function() {
            return 'list-group-item-' + this.category
        }.bind(this))
        this.category_display = ko.computed(function() {
            return (this.category.charAt(0).toUpperCase() +
                    this.category.substr(1).toLowerCase())
        }.bind(this))
        this.message_display = ko.computed(function() {
            return this.category_display() + ': ' + this.message
        }.bind(this))
    }
    return MessageModel
})
