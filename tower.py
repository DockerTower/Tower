import signal
from cement.core.exc import CaughtSignal
from cement.core.foundation import CementApp
from src.controller.builder_controller import BuilderController
from src.controller.agent_controller import AgentController
from src.controller.tower_controller import TowerController
from src.controller.nginx_controller import NginxController


class Tower(CementApp):
    class Meta:
        label = 'tower'
        handlers = [
            TowerController,
            BuilderController,
            AgentController,
            NginxController
        ]


def main():
    with Tower() as app:
        try:
            app.run()
        except CaughtSignal as e:
            if e.signum == signal.SIGINT:
                print("Stoping...")


if __name__ == '__main__':
    main()
