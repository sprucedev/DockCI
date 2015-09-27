define([
      'knockout'
    , '../util'
    , '../models/project'
    , 'text!./project_edit.html'
    , './loading_bar'
], function(ko, util, ProjectModel, template) {
    function ProjectEditModel(params) {
        finalParams = $.extend({
              'reload': false
            , 'githubEnabled': false
            , 'githubDefault': false
            , 'isNew': true
            , 'projectData': {}
            , 'messages': []
        }, params)

        finalParams['project'] = finalParams['project'] || new ProjectModel(finalParams['project_data'])

        this.loading = ko.observable(false)

        this.messages      = util.paramArray(finalParams['messages'])
        this.project       = util.param(finalParams['project'])
        this.githubEnabled = util.param(finalParams['githubEnabled'])
        this.githubDefault = util.param(finalParams['githubDefault'])
        this.isNew         = util.param(finalParams['isNew'])

        if(finalParams['reload']) {
            this.loading(true)
            this.project().reload().always(function () {
                this.loading(false)
            }.bind(this))
        }
    }

    ko.components.register('project-edit', {
        viewModel: ProjectEditModel, template: template
    })

    return ProjectEditModel
})
