define([
      'knockout'
    , 'lodash'
    , '../util'
    , 'text!./job_stage_docker_line.html'
], function(ko, _, util, template) {
    function JobStageDockerLine(params) {
        this.lines = params['lines']
        this.id = ko.observable()
        this.status = ko.observable()
        this.progress = ko.observable()
        this.progressDetail = ko.observable()
        this.error = ko.observable()

        this.message = ko.computed(function() {
            if (util.isEmpty(this.error())) {
                return this.status()
            } else {
                return this.error()
            }
        }.bind(this))

        this.showProgressText = ko.computed(function() {
            return util.isEmpty(this.progressDetail())
        }.bind(this))
        this.hasProgressBar = ko.computed(function() {
            progressDetail = this.progressDetail()
            if (
                util.isEmpty(progressDetail) ||
                _.keys(progressDetail).length <= 0
            ) {
                return false
            }
            return true
        }.bind(this))
        this.percentComplete = ko.computed(function() {
            if (!this.hasProgressBar()) { return null }

            progressDetail = this.progressDetail()

            return Math.min(
                Math.round(
                    progressDetail['current'] / progressDetail['total'] * 100
                ),
                100
            )
        }.bind(this))

        this.parseLines = function(lines) {
            newValues = {}
            keys = ['id', 'status', 'progress', 'progressDetail', 'error']

            $(lines).each(function(idx, data) {
                $(keys).each(function(idx,  key) {
                    if (!util.isEmpty(data[key])) {
                        newValues[key] = data[key]
                    }
                })
            })

            $(keys).each(function(idx,  key) {
                this[key](newValues[key])
            }.bind(this))
        }.bind(this)

        this.lines.subscribe(function(lines) {
            this.parseLines(lines)
        }.bind(this))

        this.parseLines(this.lines())
    }

    ko.components.register('job-stage-docker-line', {
        viewModel: JobStageDockerLine, template: template,
    })

    return JobStageDockerLine
})
