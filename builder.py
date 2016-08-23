import signal
from cement.core.exc import CaughtSignal
from cement.core.foundation import CementApp
from src.controller.builder_controller import BuilderController


class Tower(CementApp):
    class Meta:
        label = 'builder'
        handlers = [
            BuilderController
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
