define([
      'knockout'
    , '../util'
], function (ko, util) {
    function GithubRepoModel (params) {
        finalParams = $.extend({
              'fullId': undefined
            , 'cloneUrl': undefined
        }, params)

        this.fullId = util.param(finalParams['fullId'])
        this.cloneUrl = util.param(finalParams['cloneUrl'])

        this.account = ko.computed(function(){
            return this.fullId().split('/')[0]
        }.bind(this))
        this.shortName = ko.computed(function(){
            var parts = this.fullId().split('/')
            return parts.slice(1, parts.length).join('/')
        }.bind(this))
    }
    return GithubRepoModel
})
