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
    }
    return GithubRepoModel
})
