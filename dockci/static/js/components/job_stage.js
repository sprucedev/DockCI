define([
      'knockout'
    , '../util'
    , 'text!./job_stage.html'
], function(ko, util, template) {
    function JobStageModel(params) {
        this.slug = util.param(params['slug'])
        this.job  = util.param(params['job'])

        subscribeBus = function(bus) {
            bus.subscribe(function(message) {
                console.log(message.body)
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
