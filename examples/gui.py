#!/usr/bin/env python

from Cauldron.api import use
import os, pkg_resources
os.environ['RELDIR'] = os.path.abspath(pkg_resources.resource_filename("Cauldron", "data/reldir"))
use("local")

from Cauldron import DFW
from Cauldron.extern import GUI
SERVICE = 'testsvc'

def setup(service):
    """Setup the keywords"""
    DFW.Keyword.types['integer']("TTCAMX", service)

def main():
    """Main function."""
    
    dispatcher = DFW.Service(SERVICE, None, setup=setup)
    main_window = MainWindow(service=SERVICE)
    
    try:
        main_window.run()
    except KeyboardInterrupt:
        pass
    finally:
        main_window.shutdown()
        dispatcher.shutdown()

class MainWindow(GUI.Main.Window):
    def __init__(self, *args, **kwargs):
        service = kwargs.pop("service")
        GUI.Main.Window.__init__(self, *args, **kwargs)
        self.title ('Test Cauldron GUI')
        self.initializeService(service)
        area = self.area = GUI.Box.Color(self, background=GUI.Color.grey)
        self.ttcamx = InfoBox(area, 'TT CAM X')
        self.ttcamx.value.setKeyword(self.service['ttcamx'])
    
class InfoBox (GUI.Box.Info):

    def __init__ (self, colorbox, label, value=GUI.Value.Entry, button=None):

        GUI.Box.Info.__init__ (self, colorbox, label, value, button)

        self.grid (padx=3, pady=2)
        self.textbox.grid (padx=5, pady=4)
        self.value.grid (pady=4)

        if button != None:
            self.button.grid (padx=5, pady=4)
        

if __name__ == '__main__':
    main()