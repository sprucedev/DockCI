define(['./util'], function (util) {
    function JobBus(job, getStompClient) {
        this.subscribers = []
        this.job = util.param(job)

        this.subscribe = function(onMessage, filter) {
            this.subscribers.push([onMessage, filter])
        }.bind(this)

        this.job().getLiveQueueName(function(queueName) {
            getStompClient(function(stompClient) {
                stompClient.subscribe("/amq/queue/" + queueName, function(message) {
                    $(this.subscribers).each(function(idx, subPair) {
                        callback = subPair[0]
                        filter = subPair[1]

                        if (!util.isEmpty(filter)) {
                            if (!filter(message)) {
                                return
                            }
                        }

                        callback(message)
                    })
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
                url = 'ws://192.168.251.128:15674/ws'
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
