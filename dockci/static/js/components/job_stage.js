define([
      'knockout'
    , '../util'
    , 'text!./job_stage.html'

    , './job_stage_docker_line'
], function(ko, util, template) {
    function JobStageModel(params) {
        this.slug = util.param(params['slug'])
        this.job  = util.param(params['job'])
        this.success = util.param(params['success'])

        this.lines = ko.observableArray([]).extend({'deferred': true})
        this.lastLineType = null
        this.dockerLines = {}

        this.visibleOverride = util.param(params['visible'])

        this.togglePanel = function() {
            this.visibleOverride(!this.visible())
            return false
        }.bind(this)
        this.visible = ko.computed(function() {
            if (!util.isEmpty(this.visibleOverride())) {
                return this.visibleOverride()
            }
            if ([
                  'docker_build',
                , 'docker_test'
                , 'error'
            ].indexOf(params['slug']) != -1) {
                return true
            }
            if (this.success() === false) { return true }
            if (util.isEmpty(this.success())) { return true }
            return false
        }.bind(this))

        this.processLine = function(currentLine, line) {
            slug = this.slug()
            dockerSlugs = ['docker_push', 'docker_provision']
            data = null
            if (dockerSlugs.indexOf(slug) != -1 || slug.startsWith('utility_')) {
                if (line === '' && this.lastLineType === 'docker') { return }
                try {
                    data = JSON.parse(line)
                } catch(e) {}
            }
            if (!util.isEmpty(data)) {
                function componentData(linesArray) {
                    return {
                          'component': 'job-stage-docker-line'
                        , 'params': {
                            'lines': linesArray
                        }
                    }
                }

                if (util.isEmpty(data['id'])) {
                    linesArray = ko.observableArray()
                    this.lines.push(componentData(linesArray))

                } else if (typeof(this.dockerLines[data['id']]) === 'undefined') {
                    this.dockerLines[data['id']] = ko.observableArray()
                    linesArray = this.dockerLines[data['id']]
                    this.lines.push(componentData(linesArray))

                } else {
                    linesArray = this.dockerLines[data['id']]
                }

                linesArray.push(data)

                this.lastLineType = 'docker'
            } else {
                newLine = util.isEmpty(currentLine) || this.lastLineType !== 'plain'
                fullLine = newLine ? line : currentLine() + line
                if (slug === 'docker_build') {
                    try {
                        fullLine = JSON.parse(fullLine)['stream']
                    } catch(e) {}
                }

                if (newLine) {
                    this.lines.push(ko.observable(fullLine))
                } else {
                    currentLine(fullLine)
                }

                this.lastLineType = 'plain'
            }
        }.bind(this)

        this.updateData = function(data) {
            message_lines = data.split('\n')
            if (this.lines().length === 1) {
                while (message_lines.length !== 0 && message_lines[0].trim() === '') {
                    message_lines.shift()
                }
                if (message_lines.length === 0) {
                    return
                }
            }
            last_line = this.lines()[this.lines().length - 1]
            this.processLine(last_line, message_lines.shift())
            $(message_lines).each(function(idx, message_line) {
                this.processLine(null, message_line)
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

                $.ajax(
                      '/api/v1/projects/' + this.job().project_slug() +
                      '/jobs/' + this.job().slug() + '/stages'
                    , {
                          'data': {'slug': this.slug()}
                        , 'dataType': 'json'
                    }
                ).done(function(data) {
                    $(data).each(function(idx, stage_meta) {
                        if (!util.isEmpty(stage_meta['success'])) {
                            this.success(stage_meta['success'])
                            return false
                        }
                    }.bind(this))
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
