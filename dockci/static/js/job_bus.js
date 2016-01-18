define(['./util'], function (util) {
    function JobBus(job, getStompClient) {
        this.queues = {}
        this.job = util.param(job)

        this.createQueue = function(queueName, filter) {
            if (typeof(this.queues[queueName]) !== 'undefined') {
                throw new Error("Queue '" + queueName + "' already defined")
            }
            this.queues[queueName] = [null, filter, []]
        }.bind(this)

        this.subscribe = function(queueName, callback) {
            queue = this.queues[queueName]
            if (typeof(queue) === 'undefined') {
                throw new Error("Queue '" + queueName + "' not defined")
            }

            if (!util.isEmpty(queue[0])) {
                throw new Error("Queue '" + queueName + "' already subscribed")
            }
            queue[0] = callback

            if (queue[2].length > 0) {
                message = queue[2].shift()
                while(typeof(message) !== 'undefined') {
                    callback(message)
                    message = queue[2].shift()
                }
            }
        }.bind(this)

        this.job().getLiveQueueName(function(queueName) {
            getStompClient(function(stompClient) {
                stompClient.subscribe("/amq/queue/" + queueName, function(message) {
                    $.each(this.queues, function(key, queueData) {
                        callback = queueData[0]
                        filter = queueData[1]
                        buffer = queueData[2]

                        if (!util.isEmpty(filter)) {
                            if (!filter(message)) {
                                return true
                            }
                        }
                        if (util.isEmpty(callback)) {
                            buffer.push(message)
                            return true
                        }

                        callback(message)
                        return true
                    }.bind(this))
                }.bind(this))
            }.bind(this))
        }.bind(this))
    }
    function JobBusCont() {
        this.busses = {}
        this.stompClient = null
        this.stompClientCallbacks = []

        this.get = function(job) {
            bus = this.busses[job.slug()]
            if (typeof(bus) === 'undefined') {
                bus = new JobBus(job, this.getStompClient)
                this.busses[job.slug()] = bus
            }
            return bus
        }.bind(this)
        this.getStompClient = function(callback) {
            if (this.stompClient === null) {
                this.stompClientCallbacks.push(callback)
                url = 'ws://192.168.251.128:15674/ws'  // TODO fix this
                this.stompClient = Stomp.client(url)
                this.stompClient.connect('guest', 'guest', function() {
                    $(this.stompClientCallbacks).each(function(idx, callback_inner) {
                        callback_inner(this.stompClient)
                    }.bind(this))
                    this.stompClientCallbacks = []
                }.bind(this))
            } else {
                callback(this.stompClient)
            }
        }.bind(this)
    }

    return new JobBusCont()
})
