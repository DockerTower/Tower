import json
import os
import zmq
from threading import Thread
from uuid import uuid1
from src.core.git.git import Git
from termcolor import colored
from src.core.docker.docker import Docker


class WorkerDaemon(Thread):
    def __init__(self):
        Thread.__init__(self)
        context = zmq.Context()
        self.worker = context.socket(zmq.DEALER)
        self.worker.identity = str(uuid1()).encode('ascii')
        self.worker.connect('tcp://localhost:5573')

    identity = ""

    def run(self):
        while True:
            self.identity, msg = self.worker.recv_multipart()
            message = msg.decode('utf-8')
            message = json.loads(message)

            work = self.work(message)
            if work:
                self.log(json.dumps({
                    "success": True,
                    "data": work
                }))
            else:
                self.log(json.dumps({
                    "success": False,
                    "data": work
                }))

        self.worker.close()

    def work(self, reply):
        if reply["action"] == "build":
            return self.build(reply["data"])
        else:
            return False

    def build(self, data):
        application = data["application"]
        environment_name = data["environment"]

        environment = application["environments"][environment_name]
        services = environment["services"]
        latest = environment["latest"]

        for service_name in services:
            service = services[service_name]

            if service["repository"]["type"] == "git":

                path = "/tmp/{image}-{environment}".format(image=service["image"], environment=environment_name)
                repo = Git.repo(path)

                if os.path.isdir(path):
                    self.print("Repository exists fetching",)
                    self.print_command(repo.fetch(), color="yellow")
                    self.print("Repository fetched")
                else:
                    self.print("Repository does not exists cloning...")
                    self.print_command(Git.clone(service["repository"]["origin"], path), color="yellow")
                    self.print("Repository cloned")

                if service["tagging"] == "tag":
                    self.print("Using tagging: tag")

                    if service["repository"]["tag"] == "latest":
                        branch = tag = repo.get_last_tag()
                        self.print("Found last tag: {tag}".format(tag=tag))
                    else:
                        branch = tag = service["repository"]["tag"]
                        self.print("Using tag: {tag}".format(tag=tag))

                elif service["tagging"] == "branch":
                    self.print("Using tagging: branch")
                    branch = service["repository"]["branch"]

                self.print("Switching to branch {branch}".format(branch=branch))
                self.print_command(repo.switch_branch(branch), color="yellow")
                self.print_command(repo.pull("origin", branch), color="yellow")

                # Change working directory for docker
                os.chdir(path)
                docker = Docker()

                self.print("Building application")
                registry = "{host}:{port}".format(host=environment["registry"]["host"],
                                                  port=environment["registry"]["port"])

                branch_tagged_image = docker.get_tagged_image_name(service["image"], branch)
                tagged_images = {
                    branch_tagged_image: docker.get_tagged_image_name(service["image"], branch, registry),
                }

                if latest:
                    latest_tagged_image = docker.get_tagged_image_name(service["image"], "latest")
                    tagged_images[latest_tagged_image] = docker.get_tagged_image_name(service["image"], "latest",
                                                                                      registry)
                repository_tagged_images = []

                for tagged_image in tagged_images:
                    repository_tagged_image = tagged_images[tagged_image]
                    self.print("Building {tagged_image}".format(tagged_image=tagged_image))
                    self.print_command(docker.build(tagged_image))
                    self.print("Tagging to repository {tagged_image} -> {repository_tagged_image}".format(
                        tagged_image=tagged_image,
                        repository_tagged_image=repository_tagged_image
                    ))
                    self.print_command(docker.tag(tagged_image, repository_tagged_image))
                    self.print(
                        "Pushing {repository_tagged_image}".format(repository_tagged_image=repository_tagged_image)
                    )
                    repository_tagged_images.append(repository_tagged_image)
                    self.print_command(docker.push(repository_tagged_image))

        return repository_tagged_images

    def print(self, message, color="green"):
        self.log(colored("{message}".format(message=message), color))

    def print_command(self, command, color="blue"):
        for line in command:
            self.print(line.rstrip(), color)

    def log(self, message):
        self.worker.send_multipart([self.identity, message.encode('utf-8')])