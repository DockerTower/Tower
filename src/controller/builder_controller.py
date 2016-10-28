import os
import json
import string
import random
from requests.exceptions import HTTPError
from src.exceptions import FailedToBuildImage
from src.exceptions import FailedToCloneRepository
from src.exceptions import FailedToLoginToRegistry
from src.core.git.git import Git
from sh import ErrorReturnCode_128
from docker import Client
from docker.errors import APIError
from cement.core.controller import CementBaseController, expose


class BuilderController(CementBaseController):
    """
        Builder, builds containers
    """
    class Meta:
        label = 'builder'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Management of builders"

    repositories = {}

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # Connect client to docker, uses local docker
        self.client = Client(base_url='unix://var/run/docker.sock', version='auto')

        # Application settings, comes from environment
        self.application = json.loads(os.environ.get("APPLICATION", {})) or {}
        self.environment_name = os.environ.get("APPLICATION_ENVIRONMENT", {}) or ''

        self.environment = self.application.get("environments", {}).get(self.environment_name, {})

        # List of services in application
        self.services = self.environment.get("services", {})

    @expose(hide=True)
    def default(self):
        """
        If no command is given show help
        :return:
        """
        self.app.args.print_help()

    @expose(help="Build an image")
    def build(self):
        """
        Builds an image, command is executed by client
        :return: Outputs json
        """

        # List of all images
        images = {}

        # Login to registries
        registries = self.environment.get("registry", {})

        if type(registries) is dict:
            for registry_name, registry in registries.items():
                self.login_to_registry(registry)

        # Try building a service
        try:
            for service_name in self.services:
                service = self.services.get(service_name, {})
                service = self.build_service(service, service_name)

                images[service_name] = service

            # On success respond with json
            print(json.dumps({
                'status': 'success',
                'success': True,
                'data': images
            }))

        except FailedToLoginToRegistry as e:
            self.print('Failed to login to registry!')
            print(json.dumps({
                'status': 'failed',
                'success': False,
                'data': {
                    "message": str(e)
                }
            }))

        except FailedToBuildImage as e:
            self.print('Failed to build image!')
            print(json.dumps({
                'status': 'failed',
                'success': False,
                'data': {
                    "message": str(e)
                }
            }))

        except FailedToCloneRepository as e:
            self.print('Failed to clone repository!')
            print(json.dumps({
                'status': 'failed',
                'success': False,
                'data': {
                    "message": str(e)
                }
            }))

    def build_service(self, service, service_name):
        """
        Build a service
        :param service: Service is a list of options for service simmilar to docker-compose service v2
        :param service_name: Name of service
        :return: Returns array of images for both repository and non-private-repository images
        """

        # Array of returned images
        images = []

        # If service has repository option, tower builds image,
        # aliases and then image is pushed to registry
        repository = service.get('repository', False)

        if repository and type(repository) is dict:

            # Repository options
            repository = service.get("repository", {})
            image = repository.get('image', {})
            registries = repository.get("registry", [])

            # Image options
            aliases = image.get('aliases', [])
            image_name = image.get("name", '')

            # Docker options
            dockerfile = service.get("dockerfile", 'Dockerfile')

            origin = repository.get("origin", '')
            path = self.repositories.get(origin, False)
            if not path:
                # Set path to repository
                path = "/storage/{random}".format(random=self.create_random())

            tag = self.get_repository(repository, path)
            tagged_image = self.create_tagged_image_name(image_name, tag)

            # Build image
            # TODO: Run pre_build commands
            self.build_image(tagged_image, path, dockerfile)

            # Add tag for repository
            aliases.append(tag)

            # Create aliases by tagging repository image and
            # push it to repository
            for alias in aliases:

                # Registry image name, default without registry
                registry_image = image_name

                # Tagged image with empty registry
                registry_tagged_image = self.create_tagged_image_name(image_name, alias)

                if registries is False:
                    pass
                else:
                    # Loop through registries and push images to them
                    for registry_name in registries:
                        # If registry exists
                        if self.environment.get("registry", {}).get(registry_name, False):
                            # Create url for registry
                            host = self.environment.get("registry", {}).get(registry_name, {}).get("host", 'localhost')
                            port = self.environment.get("registry", {}).get(registry_name, {}).get("port", '5000')
                            url = "{host}:{port}".format(host=host, port=port)

                            # Registry image name
                            registry_image = self.create_registry_image_name(image_name, url)

                            # Create repository tagged image name for pushing
                            registry_tagged_image = self.create_repository_tagged_image_name(image_name, alias, url)

                            # Push image to private registry
                            self.push_image(registry_image, alias)

                # Alias image with registry and alias
                self.alias_image(tagged_image, registry_image, alias)

                # Add image to the list of images
                images.append(registry_tagged_image)
        else:
            # Append image name to images if image comes from public repository
            images.append(service.get("image", service_name))

        # Return all images
        return images

    @staticmethod
    def create_tagged_image_name(image_name, tag):
        """
        Create tagged image name
        :param image_name: Image name without tags
        :param tag: Tag for image
        :return: Returns string
        """
        return "{image}:{tag}".format(
            image=image_name,
            tag=tag
        )

    @staticmethod
    def create_registry_image_name(image_name, url):
        """
        Create registry image name
        :param url: Url of registry
        :param image_name: Image name could be tagged or without tag
        :return: Returns string
        """
        return "{registry}/{image}".format(
            image=image_name,
            registry=url
        )

    def create_repository_tagged_image_name(self, image_name, tag, url):
        """
        Create repository tagged image name
        :param url: Url for repository in format <host>:<port>
        :param image_name: Image name could be tagged or without tag
        :param tag: Tag repository
        :return: Returns string
        """
        return "{repository_image}:{tag}".format(
            tag=tag,
            repository_image=self.create_registry_image_name(image_name, url)
        )

    def alias_image(self, tagged_image, registry_image, tag):
        """
        Alias image by tagging it
        :param registry_image: Registry image name
        :param tagged_image: Use tagged image name
        :param tag: Tag to use for new image name
        :return: Returns void
        """
        self.print("Tagging image: {tagged_image} -> {repository_image}:{tag}".format(
            tagged_image=tagged_image,
            repository_image=registry_image,
            tag=tag
        ))

        # Tag image to repository
        self.client.tag(
            image=tagged_image,
            tag=tag,
            repository=registry_image
        )

    def push_image(self, registry_image, tag):
        """
        Push image to registry
        :param registry_image: Repository image name in format <registry>/<image>
        :param tag: Tag for registry image
        :return: Returns void
        """
        self.print("Pushing image to: {registry_image}".format(registry_image=registry_image))

        # Push image to registry
        for l in self.client.push(registry_image, tag=tag, stream=True, insecure_registry=True):
            # Decode and convert format from json to dict
            l = json.loads(l.decode("utf-8"))

            # Print status and progress if available
            self.print("Status: {status}:   Progress: {progress}".format(
                status=l.get("status"),
                progress=l.get("progress"),
            ))

    def build_image(self, tagged_image, path, dockerfile):
        """
        Build image for service
        :param tagged_image: Tagged image name in format: <image>:<tag>
        :param path: Path for dockerfile and build context
        :param dockerfile: Dockerfile used to build image
        :return: Returns void
        """

        # Debugging info
        self.print("Starting building application")
        self.print("Using dockerfile: {dockerfile}".format(dockerfile=dockerfile))
        self.print("Building {tagged_image}".format(tagged_image=tagged_image))

        # Try building image
        try:
            build = self.client.build(
                tag=tagged_image,
                forcerm=True,
                rm=True,
                path=path,
                stream=True,
                dockerfile=dockerfile
            )

            # Output result
            for l in build:
                l = json.loads(l.decode("utf-8")).get("stream", "")
                self.print(l.rstrip())

        except (APIError, Exception, HTTPError) as e:
            raise FailedToBuildImage(e)

    @staticmethod
    def create_random(random_range=5):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random_range))

    def get_repository(self, repository, path):
        """
        Clone the repository from git
        :param repository: Repository options
        :param path: Path for saved repository
        :return: Returns string tag for image
        """

        # Set Variables
        origin = repository.get("origin", '')
        branch = repository.get("branch", 'master')
        tag = repository.get("tag", 'latest')

        repository_path = self.repositories.get(origin, False)
        if repository_path:
            path = repository_path

        repo = Git.repo(path)

        if not repository_path:
            # Create repository
            self.print("Cloning...")

            try:
                self.print_command(Git.clone(origin, path))
            except ErrorReturnCode_128 as e:
                raise FailedToCloneRepository(e)

            self.repositories.update({origin: path})
            self.print("Repository cloned")

        tag_based = tag.split(':')

        # Get tag content
        if tag is '':
            branch = repo.get_last_commit_id(format="%H")
            tag = repo.get_last_commit_id()
        elif len(tag_based) is 2:
            branch = tag = tag_based[1]

        branch = branch.strip()
        tag = tag.strip()

        # Switch to branch for tag
        self.print("Switching to branch {branch}".format(branch=branch))
        self.print_command(repo.switch_branch(branch))

        return tag

    def login_to_registry(self, registry):
        """
        Login to remote private repository
        :return: Returns void
        """
        host = registry.get("host", 'localhost')
        port = registry.get("port", '5000')
        username = registry.get("username", '')
        password = registry.get("password", '')
        url = "{host}:{port}".format(host=host, port=port)

        self.print("Logging to {registry} as {username}".format(registry=url, username=username))
        try:
            self.client.login(registry=url, username=username, password=password)
        except APIError as e:
            raise FailedToLoginToRegistry(e)

    @staticmethod
    def print(message, end="\n"):
        print("===> {message}".format(message=message), end=end)

    def print_command(self, command):
        for line in command:
            self.print(line.rstrip())
