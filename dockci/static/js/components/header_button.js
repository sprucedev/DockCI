define([
      'knockout'
    , 'text!./header_button.html'
], function(ko, template) {
    function HeaderButtonModel(params) {
        finalParams = $.extend({
              'icon': undefined
            , 'click': (function(){})
            , 'buttonType': 'default'
        }, params)

        this.buttonType = ko.computed(function() {
            return 'btn-' + finalParams['buttonType']
        })
        this.icon = ko.computed(function () {
            if(typeof(finalParams['icon']) === 'undefined') { return '' }
            return 'glyphicon glyphicon-' + finalParams['icon']
        })
        this.click = finalParams['click']
    }

    ko.components.register('header-button', {
        viewModel: HeaderButtonModel, template: template,
    })

    return HeaderButtonModel
})
