define([
      'knockout'
    , '../util'
    , '../models/project'
    , 'text!./project_edit_dialog.html'

    , 'app/components/project_edit'
], function(ko, util, ProjectModel, template) {
    function ProjectEditDialogModel(params) {
        self = this

        reload = params['reload'] === true
        project = params['project'] || new ProjectModel(params['project_data'] || {})

        this.messages = ko.observableArray()
        this.saving = ko.observable(false)

        this.visible = params['visible']
        this.title = params['title'] || ko.observable('Edit project')
        this.action = params['action'] || function() {}
        this.github = ko.observable(params['github'])
        this.isNew = ko.observable(params['isNew'])

        this.saveLabel = ko.computed(function () {
          return self.saving() ? '<i class="mdi-device-data-usage spin"></i>' : params['saveLabel']
        })

        if(typeof(project) == 'function') {
            this.project = project
        } else {
            this.project = ko.observable(project)
        }

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
