import json
import re
import docker
import os
import argparse
from jinja2 import Environment, FileSystemLoader
from slugify import slugify
from cement.core.controller import CementBaseController, expose


class AgentController(CementBaseController):
    class Meta:
        label = 'agent'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Agent"

    builder_services = {}

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.working_dir = os.getcwd()
        self.client = docker.Client(base_url='unix://var/run/docker.sock', version='auto')

        # Application settings, comes from environment
        self.application = json.loads(os.environ.get("APPLICATION", "")) or {}
        self.application_name = self.application.get("name", '')
        self.application_name_slugify = slugify(self.application_name)
        self.environment_name = os.environ.get("APPLICATION_ENVIRONMENT", '') or ''
        self.environment = self.application.get("environments", {}).get(self.environment_name, {})
        self.services = self.environment.get("services", {})

        self.project_name = "{application}-{environment_name}".format(application=self.application_name_slugify,
                                                                      environment_name=self.environment_name)

        template_environment = Environment(loader=FileSystemLoader(self.working_dir))
        self.template = template_environment.get_template("./resources/application.conf")

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

    @expose(help="Deploy application")
    def deploy(self):
        self.builder_services = json.loads(os.environ.get("SERVICES", "")) or {}

        self.print("Deploying application")

        containers = self.client.containers(filters={
            "label": "com.tower.application={project_name}".format(project_name=self.application_name_slugify)
        })

        if not containers:
            self.print("First time deployment")

            networks = self.client.networks(names=[self.project_name])

            if not networks:
                self.print("Creating network for application as {network_name}".format(network_name=self.project_name))
                network = self.client.create_network(
                    name=self.project_name,
                    internal=False,
                    driver='bridge',
                    labels={
                        "com.tower.network": self.project_name
                    }
                )
            else:
                network = networks[0]

            self.print("Using network {network_name}".format(network_name=network.get("Name")))

            service_tree = self.dep(self.services)

            # Create containers and start them
            for group in service_tree:
                for service_name in group:
                    self.build(service_name)

        self.save()

        # On success respond with json
        print(json.dumps({
            'status': 'success',
            'success': True,
        }))

    @expose(help="Down application")
    def down(self):
        self.print("Bringing application down")

        containers = self.client.containers(filters={
            "label": "com.tower.application={project_name}".format(project_name=self.application_name_slugify)
        }, all=True)

        if containers:
            service_tree = self.dep(self.services)

            # Create containers and start them
            for group in service_tree:
                for service_name in group:
                    self.service_down(service_name)

        # On success respond with json
        print(json.dumps({
            'status': 'success',
            'success': True,
        }))

    def service_down(self, service_name):
        containers = self.client.containers(filters={
            "label": "com.tower.service={service_name}".format(service_name=service_name),
            "name": service_name,
        }, all=True)

        if containers:
            for container in containers:
                self.print("Stopping {service_name}".format(service_name=service_name))
                self.client.stop(container=container.get("Id"))
                self.client.remove_container(container=container.get("Id"))

    @staticmethod
    def dep(arg):
        """
        Dependency resolver, found at http://code.activestate.com/recipes/576570-dependency-resolver/
        :param arg: is a dependency dictionary in which the values are the dependencies of their respective keys.
        :return:
        """
        d = dict((k, set(arg[k].get("links", []) + arg[k].get("depends_on", []))) for k in arg)
        r = []
        while d:
            # values not in keys (items without dep)
            t = set(i for v in d.values() for i in v) - set(d.keys())
            # and keys without value (items without dep)
            t.update(k for k, v in d.items() if not v)
            # can be done right away
            r.append(t)
            # and cleaned up
            d = dict(((k, v - t) for k, v in d.items() if v))
        return r

    def build(self, service_name):
        self.print("Creating service: {service_name}".format(service_name=service_name))

        service = self.services.get(service_name, {})

        containers = self.client.containers(filters={
            "label": "com.tower.service={service_name}".format(service_name=service_name),
            "name": service_name,
        }, all=True)

        if not containers:

            image = service.get("image", '')

            if service.get("repository", False) and service.get("repository", {}).get("registry", False):
                self.print("Pulling {image}".format(image=image))

                for l in self.client.pull(image, stream=True):
                    # Decode and convert format from json to dict
                    l = json.loads(l.decode("utf-8"))

                    # Print status and progress if available
                    self.print("Status: {status}:   Progress: {progress}".format(
                        status=l.get("status"),
                        progress=l.get("progress"),
                    ))

            self.print("Using image: {image}".format(image=image))

            # networking_config = client.create_networking_config({
            #     project_name: client.create_endpoint_config()
            # })

            links = {}
            for link in service.get("links", {}):
                links[link] = link

            host_config = self.client.create_host_config(
                binds=None,
                port_bindings=None,
                lxc_conf=None,
                publish_all_ports=False,
                links=links,
                privileged=service.get("privileged", False),
                dns=service.get("dns", None),
                dns_search=None,
                volumes_from=service.get("volumes_from", None),
                network_mode="bridge",
                restart_policy=service.get("restart", None),
                cap_add=None,
                cap_drop=None,
                devices=None,
                extra_hosts=service.get("extra_hosts", None),
                read_only=None,
                pid_mode=None,
                ipc_mode=None,
                security_opt=None,
                ulimits=None,
                log_config=None,
                mem_limit=None,
                memswap_limit=None,
                mem_swappiness=None,
                cgroup_parent=None,
                group_add=None,
                cpu_quota=None,
                cpu_period=None,
                blkio_weight=None,
                blkio_weight_device=None,
                device_read_bps=None,
                device_write_bps=None,
                device_read_iops=None,
                device_write_iops=None,
                oom_kill_disable=False,
                shm_size=None,
                tmpfs=None,
                oom_score_adj=None,
            )

            labels = {
                "com.tower.application": self.application_name_slugify,
                "com.tower.service": service_name,
                "com.tower.application_environment": self.environment_name
            }

            service_labels = service.get("labels", {})

            labels = {**service_labels, **labels}

            container = self.client.create_container(
                image=image,
                hostname=service.get("hostname", None),
                user=service.get("user", None),
                detach=False,
                stdin_open=False,
                tty=False,
                mem_limit=service.get("mem_limit", None),
                ports=service.get("ports", None),
                environment=service.get("environment", None),
                dns=service.get("dns", None),
                volumes=service.get("volumes", None),
                network_disabled=service.get("network_disabled", False),
                entrypoint=service.get("entrypoint", None),
                cpu_shares=service.get("cpu_shares", None),
                working_dir=service.get("working_dir", None),
                domainname=service.get("domainname", None),
                memswap_limit=service.get("memswap_limit", None),
                cpuset=service.get("cpuset", None),
                mac_address=service.get("mac_address", None),
                volume_driver=service.get("volume_driver", None),
                stop_signal=service.get("stop_signal", None),
                networking_config=None,
                host_config=host_config,
                labels=labels,
                name=service_name,
            )

            container_id = container.get("Id", '')
            self.client.start(container=container_id)

            status = "Created"
            container = self.client.containers(filters={
                "label": "com.tower.service={service_name}".format(service_name=service_name),
                "name": service_name,
            }, all=True)[0]

            while status == 'Created':
                container_status = container.get("Status")
                if container_status.startswith("Up"):
                    status = "Up"
                elif container_status.startswith("Exited"):
                    status = "Exited"

            self.print("Service return status: {status}".format(status=status))

            if status == 'Up':
                for command in service.get("before_deploy_commands", {}):
                    command_parts = command.split(" ")
                    command_container = command_parts[0]

                    if command_container == service_name:
                        self.print("Executing command on container: {command}".format(command=command))
                        command = command.replace(command_container, '').lstrip()
                        exec_id = self.client.exec_create(
                            container=container_id,
                            cmd=command
                        )
                        response = self.client.exec_start(
                            exec_id=exec_id,
                            stream=True,
                            detach=False
                        )

                        for s in response:
                            self.print(s.decode('UTF-8').strip())

                    else:

                        parser = argparse.ArgumentParser(description='Docker run argument parser')

                        parser.add_argument('--privileged', action="store_true", dest="privileged", default=False)
                        parser.add_argument('--volumes-from', action="store", dest="volumes_from", type=str)
                        parser.add_argument('-p', action="store", dest="p", type=list)
                        parser.add_argument('-v', action="store", dest="v", type=list)

                        command_arguments = parser.parse_args(command_parts)

                        host_config = self.client.create_host_config(
                            publish_all_ports=False,
                            links=links,
                            privileged=command_arguments.privileged,
                            volumes_from=command_arguments.volumes_from,
                            network_mode="bridge",
                        )

                        container = self.client.create_container(
                            image=command_container,
                            detach=False,
                            stdin_open=False,
                            tty=False,
                            volumes=command_arguments.v,
                            host_config=host_config
                        )

                        container_id = container.get("Id", '')
                        self.client.start(container=container_id)

            return container_id

        else:
            self.print("Service exists {service_name}".format(service_name=service_name))

            for container in containers:
                status = container.get("Status")
                if status == 'Created' or status.startswith("Exited"):
                    container_id = container.get("Id", '')
                    self.client.start(container=container_id)

    def save(self):
        containers = self.client.containers(filters={
            "label": "com.tower.application" + "=" + self.application_name_slugify
        })

        application_containers = []

        for container in containers:
            network_mode = container.get("HostConfig", {}).get("NetworkMode", '')
            ip = container.get("NetworkSettings", {}).get("Networks").get(network_mode, {}).get("IPAddress")
            inspect = self.client.inspect_container(container.get("Id"))
            name = container.get("Name", '')
            name = name.replace("/", '')
            virtual_host = ''

            for i in inspect.get("Config", {}).get("Env", {}):
                match = re.match('VIRTUAL_HOST=\\"(.*)\\"', i)
                match2 = re.match('VIRTUAL_HOST=(.*)', i)

                if match:
                    virtual_host = match.group(1)
                elif match2:
                    virtual_host = match2.group(1)

            application_container = {
                "ServiceName": name,
                "IpAddress": ip,
                "VirtualHost": virtual_host
            }

            application_containers.append(application_container)

        if application_containers:
            for container in application_containers:
                virtual_host = container.get("VirtualHost")
                name = container.get("ServiceName")
                ip_address = container.get("IpAddress")

                if virtual_host != '':
                    nginx_configuration = self.template.render({
                        'virtual_host': virtual_host,
                        'ip_address': ip_address,
                        "port": "80"
                    })

                    with open('/etc/nginx/conf.d/' + name, 'w') as file:
                        file.write(nginx_configuration)
        return True

    @staticmethod
    def print(message, end="\n"):
        print("===> {message}".format(message=message), end=end)

    @staticmethod
    def print_stream(message, service_name):
        line = ""
        for s in message:
            s = s.decode("utf-8")

            if line.endswith('\r\n'):
                print("===> {service_name}: {message}".format(message=message, service_name=service_name))
                line = ""

            line += s
        return line
