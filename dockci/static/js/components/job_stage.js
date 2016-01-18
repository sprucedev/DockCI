define([
      'knockout'
    , '../util'
    , 'text!./job_stage.html'
], function(ko, util, template) {
    function JobStageModel(params) {
        this.slug = util.param(params['slug'])
        this.job  = util.param(params['job'])

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
                    console.log(this.slug())
                    console.dir(message)
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
