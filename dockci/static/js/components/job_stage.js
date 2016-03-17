define([
      'knockout'
    , 'lodash'
    , '../util'
    , '../models/line_buffer'
    , 'text!./job_stage.html'

    , './job_stage_docker_line'
    , './job_stage_build_step'
], function(ko, _, util, LineBuffer, template) {
    function JobStageModel(params) {
        this.slug = util.param(params['slug'])
        this.job  = util.param(params['job'])
        this.success = util.param(params['success'])

        this.lines = ko.observableArray([]).extend({'deferred': true})
        this.lastLineType = null
        this.dockerLines = {}
        this.lastBuildLines = null

        this.lineBuffer = new LineBuffer()

        this.visibleOverride = util.param(params['visible'])

        this.showIncomplete = ko.computed(function() {
            slug = this.slug()
            tranformMatches = [
                'docker_push',
                'docker_provision',
                'docker_build',
            ]
            return !(
                tranformMatches.indexOf(slug) != -1 ||
                slug.startsWith('utility_')
            )
        }.bind(this))

        this.lineBuffer.subscribeLine(function(line) {
            line = this.dockerGenericTransform(line)
            line = this.buildTransform(line)
            line = this.testTransform(line)
            return line
        }.bind(this))

        /*
         * Generic Docker stages - updatable, progress, errors
         */
        this.dockerGenericTransformDo = ko.computed(function() {
            slug = this.slug()
            dockerSlugs = ['docker_push', 'docker_provision']
            return (
                dockerSlugs.indexOf(slug) != -1 ||
                slug.startsWith('utility_')
            )
        }.bind(this))
        this.dockerGenericTransform = function(line) {
            if (!this.dockerGenericTransformDo()) { return line }
            if (line === '' && this.lastLineType === 'docker') { return null }

            try {
                data = JSON.parse(line)
            } catch(e) { return line }

            function dockerComp(linesArray) {
                return {
                      'component': 'job-stage-docker-line'
                    , 'params': {
                        'lines': linesArray
                    }
                }
            }

            if (util.isEmpty(data['id'])) {
                linesArray = ko.observableArray()
                newLine = dockerComp(linesArray)

            } else if (_.isNil(this.dockerLines[data['id']])) {
                this.dockerLines[data['id']] = ko.observableArray()
                linesArray = this.dockerLines[data['id']]
                newLine = dockerComp(linesArray)

            } else {
                linesArray = this.dockerLines[data['id']]
                newLine = null
            }

            linesArray.push(data)
            this.lastLineType = 'docker'
            return newLine

        }.bind(this)

        /*
         * Build stage - JSON with "stream" key, parsed to split steps
         */
        this.buildTransformDo = ko.computed(function() {
            return this.slug() === 'docker_build'
        }.bind(this))
        this.buildTransform = function(line) {
            if (!this.buildTransformDo()) { return line }
            if (line === '') { return null }

            try {
                data = JSON.parse(line)
            } catch(e) { return line }

            function buildComp(linesArray) {
                return {
                      'component': 'job-stage-build-step'
                    , 'params': {
                        'lines': linesArray
                    }
                }
            }

            newComponent = _.isNil(this.lastBuildLines)
            newComponent = newComponent || (
                !_.isNil(data['stream']) &&
                data['stream'].startsWith('Step ')
            )
            if (newComponent) {
                linesArray = ko.observableArray()
                newLine = buildComp(linesArray)
            } else {
                linesArray = this.lastBuildLines
                newLine = null
            }

            linesArray.push(data !== null ? data : line)
            this.lastBuildLines = linesArray
            this.lastLineType = 'build'
            return newLine

        }.bind(this)

        /*
         * Subunit (test) stage
         */
        this.testTransformDo = ko.computed(function() {
            return this.slug() === 'docker_test'
        }.bind(this))
        this.testTransform = function(line) {
            if (!this.testTransformDo()) { return line }

            try {
                data = JSON.parse(line)
            } catch(e) { return line }

            if (data['file_name'] === 'otherthings') {
                this.updateData(data['file_bytes'])

            } else {
                linesArray = this.lastBuildLines
                newLine = null
            }

            this.lastLineType = 'test'
            return null

        }.bind(this)

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

        this.updateData = function(data) {
            this.lineBuffer.append(data)
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
