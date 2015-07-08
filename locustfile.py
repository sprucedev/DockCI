"""
Locust is an easy-to-use, distributed, user load testing tool.

This is the locust test file for a DockCI instance
"""

from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    @task(2)
    def index(self):
        self.client.get('/')

    @task(1)
    def project(self):
        self.client.get("/projects/dockci")

class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait=5000
    max_wait=9000
