define([
    'knockout'
  , '../util'
  , 'text!./project_delete_dialog.html'
], function(ko, util, template) {
  function ProjectDeleteDialogModel(params) {
    finalParams = $.extend({
        'visible': false
      , 'title': 'Delete project'
    }, params)

    this.messages = ko.observableArray()
    this.saving   = ko.observable(false)

    this.project   = util.param(finalParams['project'])
    this.visible   = util.param(finalParams['visible'])
    this.title     = util.param(finalParams['title'])

    this.deleteAction = function () {
      self = this
      self.saving(true)
      self.project().delete().always(function() {
        self.saving(false)
      }).done(function(jobData) {
        window.location.href = '/'
      }).fail(util.ajax_fail(self.messages))
    }.bind(this)
  }

  ko.components.register('project-delete-dialog', {
    viewModel: ProjectDeleteDialogModel, template: template
  })

  return ProjectDeleteDialogModel
})
