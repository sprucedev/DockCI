define([
      'knockout'
    , '../util'
], function (ko, util) {
    function GitlabRepoModel (params) {
        finalParams = $.extend({
              'fullId': undefined
            , 'fullName': undefined
            , 'cloneUrl': undefined
        }, params)

        this.fullId = util.param(finalParams['fullId'])
        this.fullName = util.param(finalParams['fullName'])
        this.cloneUrl = util.param(finalParams['cloneUrl'])

        this.account = ko.computed(function(){
            return this.fullId().split('/')[0].trim()
        }.bind(this))
        this.shortName = ko.computed(function(){
            var parts = this.fullId().split('/')
            return parts.slice(1, parts.length).join('/').trim()
        }.bind(this))
    }
    return GitlabRepoModel
})
