#!/usr/bin/env python

from Cauldron.api import use
import click
import os, pkg_resources
os.environ['RELDIR'] = os.path.abspath(pkg_resources.resource_filename("Cauldron", "data/reldir"))


def setup(service):
    """Setup the keywords"""
    from Cauldron import DFW
    DFW.Keyword.types['integer']("TTCAMX", service)

@click.command()
@click.option("-k", "--backend", default='local', help="Cauldron backend to use.")
@click.option("-s", "--service", default='testsvc', help="Service to use")
def main(backend, service):
    """Main function."""
    use(backend)
    from Cauldron import DFW
    dispatcher = DFW.Service(service, None, setup=setup)
    
    with dispatcher:
        MainWindow = define_mainwindow()
        main_window = MainWindow(service=service)
        try:
            main_window.run()
        except KeyboardInterrupt:
            pass
        finally:
            main_window.shutdown()

def define_mainwindow():
    """Guard the GUI import from uninitialized KTL."""
    from Cauldron.extern import GUI
    class InfoBox (GUI.Box.Info):

        def __init__ (self, colorbox, label, value=GUI.Value.Entry, button=None):

            GUI.Box.Info.__init__ (self, colorbox, label, value, button)

            self.grid (padx=3, pady=2)
            self.textbox.grid (padx=5, pady=4)
            self.value.grid (pady=4)

            if button != None:
                self.button.grid (padx=5, pady=4)
    
    class MainWindow(GUI.Main.Window):
        def __init__(self, *args, **kwargs):
            service = kwargs.pop("service")
            GUI.Main.Window.__init__(self, *args, **kwargs)
            self.title ('Test Cauldron GUI')
            self.initializeService(service)
            area = self.area = GUI.Box.Color(self, background=GUI.Color.grey)
            self.ttcamx = InfoBox(area, 'TT CAM X')
            self.ttcamx.value.setKeyword(self.service['ttcamx'])
    return MainWindow

if __name__ == '__main__':
    main()