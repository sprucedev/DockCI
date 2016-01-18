define([
      'knockout'
    , '../util'
    , 'text!./job_stage.html'
], function(ko, util, template) {
    function JobStageModel(params) {
        this.slug = util.param(params['slug'])
        this.job  = util.param(params['job'])
        this.success = util.param(params['success'])

        this.lines = ko.observableArray([ko.observable('')])

        this.updateData = function(data) {
            message_lines = data.split('\n')
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
        }.bind(this)

        this.consumeLiveContent = function() {
            this.job().bus().subscribe(this.slug(), function(message) {
                if (message.headers.destination.endsWith('.content')) {
                    this.updateData(message.body)
                } else if (message.headers.destination.endsWith('.status')) {
                    success = JSON.parse(message.body)['success']
                    if (!util.isEmpty(success)) {
                        this.success(success)
                    }
                }
            }.bind(this))
        }.bind(this)

        this.getInitLoadUrl = function(callback) {
            this.job().getLiveLoadDetail(function(live_load_detail) {
                slug = this.slug()

                if (slug === live_load_detail['init_stage']) {
                    return callback(live_load_detail['init_log'])
                }

                stage_idx = this.job().job_stage_slugs.indexOf(slug)
                live_stage_idx = this.job().job_stage_slugs.indexOf(live_load_detail['init_stage'])
                if (stage_idx >= 0 && stage_idx < live_stage_idx) {
                    url_parts = live_load_detail['init_log'].split('/')
                    url_parts[url_parts.length - 1] = slug
                    return callback(url_parts.join('/'))
                }

                return callback(null)
            }.bind(this))
        }.bind(this)

        this.initLogBytes = 0
        this.getInitLoadUrl(function(init_load_url) {
            if (!util.isEmpty(init_load_url)) {
                $.ajax({
                      'url': init_load_url
                    , 'dataType': 'json'
                    , 'xhrFields': {
                        'onprogress': function(event) {
                            responseText = event.target.responseText
                            totalLength = responseText.length
                            responseText = responseText.substr(this.initLogBytes,
                                                               responseText.length)
                            this.initLogBytes = totalLength
                            this.updateData(responseText)
                        }.bind(this)
                    }
                }).complete(function() {
                    this.consumeLiveContent()
                }.bind(this))
            } else {
                this.consumeLiveContent()
            }
        }.bind(this))
    }
    JobStageModel.contentFilterFor = function(project_slug, job_slug, stage_slug) {
        return function(message) {
            parts = message.headers.destination.split('.')
            return (
                parts[parts.length - 2] === stage_slug &&
                parts[parts.length - 3] === job_slug &&
                parts[parts.length - 4] === project_slug
            )
        }
    }

    ko.components.register('job-stage', {
        viewModel: JobStageModel, template: template,
    })

    return JobStageModel
})
