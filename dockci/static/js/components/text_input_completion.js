define([
    'knockout'
  , 'lodash'
  , '../util'
  , 'text!./text_input_completion.html'
], function(ko, _, util, template) {
  function TextInputCompletionModel(params) {
    finalParams = $.extend({
        'completions': []
      , 'value': ko.observable('')
      , 'click': function() {}
    }, params)

    this.completions = util.paramArray(finalParams['completions'])
    this.value = finalParams['value']

    this._clickHandler = finalParams['click']

    this._completionIndexPair = ko.computed(function() {
      var i, j, slug, label, key, iList = [], iLookup = {}, completions = this.completions()
      for (i = 0; i < completions.length; i++) {
        slug = completions[i][0]
        for (j = 0; j < completions[i].length; j++) {
          key = completions[i][j].toLowerCase()
          iList.push([slug, key])
          iLookup[key] = completions[i]
        }
      }
      return [iList, iLookup]
    }.bind(this))
    this.indexedCompletionKeys = ko.computed(function() {
      return this._completionIndexPair()[0]
    }.bind(this))
    this.indexedCompletionLookup = ko.computed(function() {
      return this._completionIndexPair()[1]
    }.bind(this))

    this.validCompletionKeys = ko.computed(function() {
      var index = this.indexedCompletionKeys(), value = this.value()
      return _.filter(index, function(indexItem) {
        var key = indexItem[1]
        return key.startsWith(value)
      })
    }.bind(this))
    this.validCompletions = ko.computed(function() {
      var lookup = this.indexedCompletionLookup()
      return _.map(
        _.uniq(_.map(
          this.validCompletionKeys(),
          function(pair) { return pair[0] }
        )),
        function(key) { return lookup[key] }
      )
    }.bind(this))

    this.inputFocus = ko.observable()
    this.inputFocus.extend({rateLimit:100})

    this.completionClick = function(completion) {
      this.value(completion[0])
      this._clickHandler(completion[0])
    }.bind(this)
  }

  ko.components.register('text-input-completion', {
      viewModel: TextInputCompletionModel, template: template,
  })

  return TextInputCompletionModel
})
