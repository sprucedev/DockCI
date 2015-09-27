define([
      'knockout'
    , '../util'
    , '../models/project'
    , 'text!./project_edit_dialog.html'

    , 'app/components/project_edit'
], function(ko, util, ProjectModel, template) {
    function ProjectEditDialogModel(params) {
        finalParams = $.extend({
              'visible': false
            , 'reload': false
            , 'title': 'Edit project'
            , 'action': (function(){})
            , 'githubEnabled': false
            , 'githubDefault': false
            , 'isNew': true
            , 'projectData': {}
        }, params)

        finalParams['project'] = finalParams['project'] || new ProjectModel(finalParams['project_data'])

        this.messages = ko.observableArray()
        this.saving = ko.observable(false)
        this.action = finalParams['action']

        this.saveLabel = ko.computed(function () {
          return this.saving() ? '<i class="mdi-device-data-usage spin"></i>' : (finalParams['saveLabel'] || "Save")
        }.bind(this))

        this.project       = util.param(finalParams['project'])
        this.visible       = util.param(finalParams['visible'])
        this.title         = util.param(finalParams['title'])
        this.githubEnabled = util.param(finalParams['githubEnabled'])
        this.githubDefault = util.param(finalParams['githubDefault'])
        this.isNew         = util.param(finalParams['isNew'])

        this.saveProject = function () {
            self = this
            self.saving(true)
            self.project().save(this.isNew()).always(function() {
                self.saving(false)
            }).done(function(project_data) {
                self.project().reload_from(project_data)
                self.visible(false)
                self.action(project_data)
            }).fail(util.ajax_fail(self.messages))
        }.bind(this)
    }

    ko.components.register('project-edit-dialog', {
        viewModel: ProjectEditDialogModel, template: template
    })

    return ProjectEditDialogModel
})
