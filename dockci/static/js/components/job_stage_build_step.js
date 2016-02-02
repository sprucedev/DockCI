define([
      'knockout'
    , '../util'
    , 'text!./job_stage_build_step.html'
], function(ko, util, template) {
    function JobStageBuildStepModel(params) {
        this.lines = params['lines']
        this.cached = ko.observable(false)
        this.visible = ko.observable(true)

        this.processLine = function(line) {
            stream = line['stream'].trimRight()
            if (stream === ' ---> Using cache') { this.cached(true) }
        }.bind(this)
        this.lines.subscribe(function(value) {
            lastLine = value[value.length - 1]
            this.processLine(lastLine)
        }.bind(this))
        $(this.lines()).each(function(idx, line) {
            this.processLine(line)
        }.bind(this))

        this.cached.subscribe(function(value) {
            if (value) { this.visible(false) }
        }.bind(this))
    }

    ko.components.register('job-stage-build-step', {
        viewModel: JobStageBuildStepModel, template: template,
    })

    return JobStageBuildStepModel
})
