define([
      'knockout'
    , '../util'
    , 'text!./loading_bar.html'
], function(ko, util, template) {
    function LoadingBarModel(params) {
        finalParams = $.extend({
              'visible': true
        }, params)

        this.visible = util.param(finalParams['visible'])
    }

    ko.components.register('loading-bar', {
        viewModel: LoadingBarModel, template: template,
    })

    return LoadingBarModel
})
