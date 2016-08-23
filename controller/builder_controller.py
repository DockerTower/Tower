from cement.core.controller import CementBaseController, expose
from core.tower.thread.worker_daemon import WorkerDaemon


class BuilderController(CementBaseController):
    class Meta:
        label = 'base'
        description = "Management of builders"

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

    @expose(help="Start a builder", aliases=['up'])
    def start(self):
        worker = WorkerDaemon()
        worker.setDaemon(True)
        worker.start()

        while True:
            pass

