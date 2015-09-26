define([
      'knockout'
    , 'text!./header_button.html'
], function(ko, template) {
    function HeaderButtonModel(params) {
        this.icon = ko.computed(function () { return 'mdi-' + params['icon'] })
        this.click = params['click'] || function () {}
    }

    ko.components.register('header-button', {
        viewModel: HeaderButtonModel, template: template,
    })

    return HeaderButtonModel
})
