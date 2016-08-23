from sh import docker


class Docker(object):
    def __init__(self):
        self.docker = docker

    def build(self, tagged_image, dockerfile="Dockerfile"):
        return self.docker.build("--force-rm", "-f", dockerfile, "-t", tagged_image, ".", _err_to_out=True, _iter=True)

    def push(self, tagged_image):
        return self.docker.push(tagged_image, _err_to_out=True, _iter=True)

    def tag(self, tagged_image, registry_tagged_image):
        return self.docker.tag(tagged_image, registry_tagged_image, _err_to_out=True, _iter=True)

    def get_tagged_image_name(self, image, tag, repository=""):
        if repository != "":
            repository += "/"
        return "{repository}{image}:{tag}".format(image=image, tag=tag, repository=repository)
