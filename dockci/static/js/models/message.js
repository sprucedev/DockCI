define(['knockout'], function (ko) {
    return function (init_hash) {
        var self = this

        self.message = init_hash['message']
        self.category = init_hash['category']

        self.category_css = ko.computed(function() {
            return 'list-group-item-' + self.category
        })
        self.category_display = ko.computed(function() {
            return (self.category.charAt(0).toUpperCase() +
                    self.category.substr(1).toLowerCase())
        })
        self.message_display = ko.computed(function() {
            return self.category_display() + ': ' + self.message
        })
    }
})
