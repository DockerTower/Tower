import sh
from cement.core.controller import CementBaseController, expose


class NginxController(CementBaseController):
    class Meta:
        label = 'nginx'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Nginx"

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

    @expose(help="Start server")
    def start(self):
        self.print("Starting server")
        sh.nginx("-g", 'daemon off;')

    @expose(help="Reload server")
    def reload(self):
        self.print("Reloading server")
        sh.nginx("-s", 'reload')

    @expose(help="Stopping server")
    def stop(self):
        self.print("Stopping server")
        sh.nginx("-s", 'stop')

    @staticmethod
    def print(message, end="\n"):
        print("===> {message}".format(message=message), end=end)
