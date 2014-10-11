#!/usr/bin/env python2.7

# GrrProxy is a simple GUI tool to manage proxy settings in linux.
# Copyright (C) 2014 Cadogan West

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Contact the author via email: ultrabook@email.com


NAME = 'GrrProxy'
VERSION = '1.0'
DESCRIPTION = 'GrrProxy is a simple GUI tool to manage proxy settings in '\
              'linux.'
DEVELOPERS = {'Cadogan West': 'ultrabook@email.com'}


import logging
import os
import sys
import traceback
import wx

from mainframe import GrrFrame


def ExceptionHook(exctype, value, trace):
    """
    Report and log unexpected errors.
    """
    exc = traceback.format_exception(exctype, value, trace)
    ftrace = ''.join(exc)
    logging.error(ftrace)
    app = wx.GetApp()
    if app:
        wx.MessageBox('An unexpected error has occured!\n'
                      'Traceback is logged to /var/log/grrproxy.log',
                      style=wx.ICON_ERROR | wx.OK)
        app.Exit()
    else:
        sys.stderr.write(ftrace)


class GrrApp(wx.App):

    def OnInit(self):
        # Set custom exception hook (feedback + logging)
        sys.excepthook = ExceptionHook

        # Check user privileges before proceeding
        if os.getuid() != 0:
            wx.MessageBox(message='This program requires root privileges.',
                          caption='User Privileges',
                          style=wx.OK | wx.ICON_EXCLAMATION)
            return False
        else:
            # Log to file (debug) and console (info)
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s '
                                       '%(levelname)-8s %(message)s',
                                datefmt='%m-%d %H:%M',
                                filename='/var/log/grrproxy.log',
                                filemode='w')
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(name)-12s: %(levelname)-8s '
                                          '%(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

            self.frame = GrrFrame(parent=None,
                                  title='{} v{}'.format(NAME, VERSION))
            self.SetTopWindow(self.frame)
            self.frame.Show()
            return True

    def GetName(self):
        return NAME

    def GetVersion(self):
        return VERSION

    def GetCopyright(self):
        return 'Copyright (C) 2014 Cadogan West'

    def GetDescription(self):
        return DESCRIPTION

    def GetDevelopers(self):
        return ['{}: {}'.format(auth, email)
                for auth, email in DEVELOPERS.items()]

    def OnExit(self):
        logging.info('Exiting...')


if __name__ == '__main__':
    app = GrrApp(False)
    app.MainLoop()
