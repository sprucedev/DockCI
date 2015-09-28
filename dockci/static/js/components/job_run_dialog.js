define([
    'knockout'
  , '../util'
  , 'text!./job_run_dialog.html'
], function(ko, util, template) {
  function RunJobDialogModel(params) {
    finalParams = $.extend({
        'commitRef': ''
      , 'visible': false
      , 'title': 'Queue new job'
    }, params)

    this.messages = ko.observableArray()
    this.saving   = ko.observable(false)

    this.project   = util.param(finalParams['project'])
    this.commitRef = util.param(finalParams['commitRef'])
    this.visible   = util.param(finalParams['visible'])
    this.title     = util.param(finalParams['title'])

    this.queueJob = function () {
      self = this
      self.saving(true)
      self.project().queueJob(this.commitRef()).always(function() {
        self.saving(false)
      }).done(function(jobData) {
        window.location.href = '/projects/' + self.project().slug() + '/jobs/' + jobData['slug']
      }).fail(util.ajax_fail(self.messages))
    }.bind(this)
  }

  ko.components.register('job-run-dialog', {
    viewModel: RunJobDialogModel, template: template
  })

  return RunJobDialogModel
})
