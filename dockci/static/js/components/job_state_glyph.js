define([
      'knockout'
    , '../util'
    , 'text!./job_state_glyph.html'
], function(ko, util, template) {
    function JobStateGlyphModel(params) {
        this.state = util.param(params['state'])
    }

    ko.components.register('job-state-glyph', {
        viewModel: JobStateGlyphModel, template: template,
    })

    return JobStateGlyphModel
})
