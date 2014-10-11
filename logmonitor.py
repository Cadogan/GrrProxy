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


import logging
import tempfile
import threading
import time


class LogMonitor(threading.Thread):

    def __init__(self, caller, handler, event, interval=0.01):
        """
        'caller' must be the thread object of the caller.
        'handler' must the callable used for handling the logs
        'event' is the Event object which is checked before making calls to the
        handler.
        'interval' must be of type int or float. It specifies the time in
        seconds between each call to the handler. (default: 1)

        NOTE:
        If the interval is too long, the accumulated messages in the logger
        would be handled at once. For more responsive updates, keep this value
        somewhere close to one second or less (but not zero).
        """
        super(LogMonitor, self).__init__()
        self.caller = caller
        self.handler = handler
        self.event = event
        self.interval = interval
        # Define a file handler with a tempfile
        self.tfile = tempfile.NamedTemporaryFile()
        tfilehand = logging.FileHandler(self.tfile.name)
        # Set logging level
        tfilehand.setLevel(logging.INFO)
        # Create a console friendly formatter
        formatter = logging.Formatter('%(name)-12s: %(levelname)-8s '
                                      '%(message)s')
        tfilehand.setFormatter(formatter)
        # Add this handler to the root logger
        logging.getLogger('').addHandler(tfilehand)

        self.start()

    def run(self):
        """Read the logger and handle the data.

        This method enters a loop which is not broken out of until the caller
        thread is dead. The messages pushed to the logger are passed to the
        handler if the event is set. The loop is repeated in specified
        intervals.
        """
        while self.caller.is_alive():
            details = self.tfile.read()
            if self.event.is_set() and details:
                self.handler(details)
            time.sleep(self.interval)
        else:
            logging.debug('Caller thread, {}, is not alive. '
                          'LogMonitor is exiting now.'.format(self.caller))
