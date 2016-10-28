from cement.core.controller import CementBaseController, expose


class TowerController(CementBaseController):
    class Meta:
        label = 'base'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Tower"

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()
