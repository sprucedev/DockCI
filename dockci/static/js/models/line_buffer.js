define(['knockout', 'lodash'], function (ko, _) {
    function LineBuffer (split) {
        this.incompleteLine = ko.observable('')
        this.buffer = ko.observableArray([]).extend({'deferred': true})
        this.split = _.isNil(split) ? '\n' : split

        this._newLineSubscriptions = []
        this._newDataSubscriptions = []

        this.append = function(data) {
            if (_.isArray(data)) {
                lines = _.flatten(_.map(data, function(val) {
                    return val.split(this.split)
                }))
            } else {
                lines = data.split(this.split)
            }

            incompleteLine = this.incompleteLine() + lines.pop()

            lines = _.filter(
                _.map(
                    lines,
                    function(line) {
                        return _.reduce(
                            this._newLineSubscriptions,
                            function(innerLine, callback) {
                                return callback(innerLine)
                            }.bind(this),
                            line
                        )
                    }.bind(this)
                ),
                function(line) { return !_.isNil(line) }.bind(this)
            )
            _.reduce(this._newDataSubscriptions, function(innerLine, callback) {
                return callback(innerLine)
            }.bind(this), incompleteLine)

            this.buffer.push.apply(this.buffer, lines)
            this.incompleteLine(incompleteLine)
        }.bind(this)

        this.subscribeLine = function(callback) { this._newLineSubscriptions.push(callback) }
        this.subscribeData = function(callback) { this._newDataSubscriptions.push(callback) }
    }
    return LineBuffer
})
