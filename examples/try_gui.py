#!/usr/bin/env python

from Cauldron.api import use, install
import os, pkg_resources
os.environ['RELDIR'] = os.path.abspath(pkg_resources.resource_filename("Cauldron", "data/reldir"))
use("zmq")
from Cauldron.extern import GUI


def main():
    """Main function."""
    
    main_window = MainWindow()
    
    try:
        main_window.run()
    except KeyboardInterrupt:
        pass
    main_window.shutdown()
    

class MainWindow(GUI.Main.Window):
    def __init__(self, *args, **kwargs):
        GUI.Main.Window.__init__(self, *args, **kwargs)
        self.title ('Test Cauldron GUI')
        self.initializeService ('testsvc')
        area = self.area = GUI.Box.Color(self, background=GUI.Color.grey)
        self.ttcamx = InfoBox(area, 'TT CAM X')
        self.ttcamx.value.setKeyword(self.service['ttcamx'])
    
class InfoBox (GUI.Box.Info):

    def __init__ (self, colorbox, label, value=GUI.Value.Entry, button=GUI.Button.Status):

        GUI.Box.Info.__init__ (self, colorbox, label, value, button)

        self.grid (padx=3, pady=2)
        self.textbox.grid (padx=5, pady=4)
        self.value.grid (pady=4)

        if button != None:
            self.button.grid (padx=5, pady=4)
        

if __name__ == '__main__':
    main()