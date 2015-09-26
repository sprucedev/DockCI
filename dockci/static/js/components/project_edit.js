define([
      'knockout'
    , '../models/project'
    , 'text!./project_edit.html'
], function(ko, ProjectModel, template) {
    function ProjectEditModel(params) {
        reload = params['reload'] === true
        project = params['project'] || new ProjectModel(params['project_data'] || {})

        this.loading = ko.observable(reload)
        this.saving = ko.observable(false)
        this.github = ko.observable(params['github'])
        this.isNew = ko.observable(params['isNew'])

        if(typeof(project) === 'function') {
            this.project = project
        } else {
            this.project = ko.observable(project)
        }
        if(typeof(params['messages']) === 'function') {
            this.messages = params['messages']
        } else {
            this.messages = ko.observableArray(params['messages'])
        }

        if(reload) {
            this.project().reload().always(function () {
                this.loading(false)
            })
        }
    }

    ko.components.register('project-edit', {
        viewModel: ProjectEditModel, template: template
    })

    return ProjectEditModel
})
