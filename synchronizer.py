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

import threading
import wx


class Synchronizer(object):
    """
    Make synchronized calls to the GUI.
    """

    def __init__(self, func, args=(), kwargs={}):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.event = threading.Event()

    def asynchwrapper(self):
        try:
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
        # Call is made, set the event
        self.event.set()

    def run(self):
        wx.CallAfter(self.asynchwrapper)
        # Wait until the call is made
        self.event.wait()
        try:
            return self.result
        except:
            return self.exception
