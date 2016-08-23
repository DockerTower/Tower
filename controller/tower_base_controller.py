from cement.core.controller import expose
from controller.TowerController import TowerController

VERSION = '0.0.1'
BANNER = """
Tower v%s
Copyright (c) 2016 VeeeneX
""" % VERSION


class TowerBaseController(TowerController):
    class Meta:
        label = 'base'
        description = "Tower orchestrated dockercompose"
        arguments = [
            (['-v', '--version'], dict(action='version', version=BANNER)),
        ]

    @expose(help="base controller default command", hide=True)
    def default(self):
        self.app.args.print_help()
