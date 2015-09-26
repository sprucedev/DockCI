define(['jquery', 'knockout'], function ($, ko) {
    return function (init_hash) {
        var self = this

        self.slug = ko.observable()
        self.name = ko.observable()
        self.repo = ko.observable()
        self.utility = ko.observable()

        self.github_repo_id = ko.observable()

        self.hipchat_room = ko.observable()
        self.hipchat_api_token = ko.observable()

        self.link = ko.computed(function() { return '/projects/' + self.slug() })
        self.type_text = ko.computed(function() { return self.utility() ? 'utility' : 'project' })

        self.form_json = ko.computed(function() {
            return {
                'name': self.name(),
                'repo': self.repo(),
                'utility': self.utility(),
                // 'github_repo_id': self.github_repo_id(),
                'hipchat_room': self.hipchat_room(),
                'hipchat_api_token': self.hipchat_api_token(),
            }
        })

        self.reload_from = function (data) {
            self.slug(data['slug'] || '')
            self.name(data['name'] || '')
            self.repo(data['repo'] || '')
            self.utility(data['utility'] || false)
            self.github_repo_id(data['github_repo_id'] || '')
            self.hipchat_room(data['hipchat_room'] || '')
        }

        self.reload = function () {
            return $.ajax("/api/v1/projects/" + self.slug(), {
                  'dataType': 'json'
            }).done(function(data) {
                self.reload_from(data)
            })
        }

        self.save = function(isNew) {
            return $.ajax("/api/v1/projects/" + self.slug(), {
                  'method': isNew === true ? 'PUT' : 'POST'
                , 'data': self.form_json()
                , 'dataType': 'json'
            })
        }

        self.reload_from(init_hash)
    }
})
