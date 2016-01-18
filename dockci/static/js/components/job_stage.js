define([
      'knockout'
    , '../util'
    , 'text!./job_stage.html'
], function(ko, util, template) {
    function JobStageModel(params) {
        this.slug = util.param(params['slug'])
        this.job  = util.param(params['job'])

        this.lines = ko.observableArray([ko.observable('')])

        this.sourceQueue = ko.computed(function() {
            return [
                  'dockci'
                , this.job().project_slug()
                , this.job().slug()
                , this.slug()
            ].join('.')
        }.bind(this))
        this.sourceQueueContent = ko.computed(function() {
            return [
                  this.sourceQueue()
                , 'content'
            ].join('.')
        }.bind(this))

        subscribeBus = function(bus) {
            bus.subscribe(function(message) {
                if (message.headers.destination.endsWith(this.sourceQueueContent())) {
                    message_lines = message.body.split('\n')
                    if (this.lines().length === 1) {
                        while (message_lines.indexOf('') === 0) {
                            message_lines.shift()
                        }
                        if (message_lines.length === 0) {
                            return
                        }
                    }
                    last_line = this.lines()[this.lines().length - 1]
                    last_line(last_line() + message_lines.shift())
                    $(message_lines).each(function(idx, message_line) {
                        this.lines.push(ko.observable(message_line))
                    }.bind(this))
                }
            }.bind(this))
        }.bind(this)
        currentBus = this.job().bus()
        if (typeof(currentBus) === 'undefined') {
            this.job().bus.subscribe(function(bus) {
                subscribeBus(bus)
            })
        } else {
            subscribeBus(currentBus)
        }
    }

    ko.components.register('job-stage', {
        viewModel: JobStageModel, template: template,
    })

    return JobStageModel
})
