define([
    'knockout'
  , '../util'
  , 'text!./tag_pill.html'
], function(ko, util, template) {
  function TagPillModel(params) {
    finalParams = $.extend({
        'click': function() {}
      , 'enabled': true
    }, params)

    this._clickHandler = util.param(finalParams['click'])
    this.enabled = util.param(finalParams['enabled'])

    this.handleClick = function() {
      if (!this.enabled()) { return }
      return this._clickHandler()
    }.bind(this)
  }

  ko.components.register('tag-pill', {
    viewModel: TagPillModel, template: template,
  })

  return TagPillModel
})
