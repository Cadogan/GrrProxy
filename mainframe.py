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


import itertools
import logging
import threading
import wx

import backend
from propdialog import PropDialog
from logmonitor import LogMonitor
from synchronizer import Synchronizer


class GrrFrame(wx.Frame):

    def __init__(self, *args, **kwargs):
        super(GrrFrame, self).__init__(*args, **kwargs)
        self.dlg_properties = None

        self.pnl_main = wx.PyPanel(self)
        self.stb_proxset = wx.StaticBox(self.pnl_main, label='Proxy Settings')
        self.stt_http = wx.StaticText(self.pnl_main, label='http')
        self.tct_hosthttp = wx.TextCtrl(self.pnl_main, name='host')
        self.tct_porthttp = wx.TextCtrl(self.pnl_main, name='port')
        self.stt_https = wx.StaticText(self.pnl_main, label='https')
        self.tct_hosthttps = wx.TextCtrl(self.pnl_main, name='host')
        self.tct_porthttps = wx.TextCtrl(self.pnl_main, name='port')
        self.stt_ftp = wx.StaticText(self.pnl_main, label='ftp')
        self.tct_hostftp = wx.TextCtrl(self.pnl_main, name='host')
        self.tct_portftp = wx.TextCtrl(self.pnl_main, name='port')
        self.stt_socks = wx.StaticText(self.pnl_main, label='socks')
        self.tct_hostsocks = wx.TextCtrl(self.pnl_main, name='host')
        self.tct_portsocks = wx.TextCtrl(self.pnl_main, name='port')
        self.btn_applyprox = wx.Button(self.pnl_main, label='Apply Proxy')
        self.btn_removeprox = wx.Button(self.pnl_main, label='Remove Proxy')
        self.btn_properties = wx.Button(self.pnl_main, wx.ID_PROPERTIES)
        self.btn_about = wx.Button(self.pnl_main, wx.ID_ABOUT)
        self.btn_togdetails = wx.Button(self.pnl_main, label='Show Details')
        self.tct_details = wx.TextCtrl(self.pnl_main,
                                       style=wx.TE_READONLY | wx.TE_MULTILINE)

        # Group like widgets in to tuples for easy handling
        self.wid_protos = (self.stt_http, self.stt_https,
                           self.stt_ftp, self.stt_socks)
        self.wid_hosts = (self.tct_hosthttp, self.tct_hosthttps,
                          self.tct_hostftp, self.tct_hostsocks)
        self.wid_ports = (self.tct_porthttp, self.tct_porthttps,
                          self.tct_portftp, self.tct_portsocks)

        for widget in itertools.chain(self.wid_hosts, self.wid_ports):
            widget.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
            widget.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
            widget.SetValue(widget.GetName())

        # Fire up the log monitor
        self.tct_details.Hide()
        self.lmevent = threading.Event()
        self.lmthread = LogMonitor(threading.current_thread(),
                                   self.OnUpdateDetails,
                                   self.lmevent)

        self.Bind(wx.EVT_BUTTON, self.OnRemoveProxy, self.btn_removeprox)
        self.Bind(wx.EVT_BUTTON, self.OnProperties, self.btn_properties)
        self.Bind(wx.EVT_BUTTON, self.OnToggleDetails, self.btn_togdetails)
        self.Bind(wx.EVT_BUTTON, self.OnApplyProxy, self.btn_applyprox)
        self.Bind(wx.EVT_BUTTON, self.OnAbout, self.btn_about)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.DoLayout()

    def OnApplyProxy(self, event):
        logging.info('Applying proxy settings...')
        # Gather hosts and ports
        protos, hosts, ports = [], [], []
        for wpro, whos, wpor in zip(self.wid_protos,
                                    self.wid_hosts,
                                    self.wid_ports):
            host = whos.GetValue()
            # Proceed if host is specified
            if host != whos.GetName():
                hosts.append(host)
                protos.append(wpro.GetLabel())
                port = wpor.GetValue()
                if port != wpor.GetName():
                    ports.append(port)
                else:
                    # No port is specified, get default
                    ports.append(backend.DEFAULT_PORT)

        # Return if no host is specified
        if not hosts:
            logging.info('No hosts were specified.')
            return

        for proto, host, port in zip(protos, hosts, ports):
            logging.info('Protocol: {}, Host: {}, Port: {}'
                         .format(proto, host, port))

        if self.dlg_properties:
            # Gather additional settings from dialog
            authtexts = self.dlg_properties.GetAuthTexts()
            user, pwd = authtexts if authtexts else (None, None)
            useauth = self.dlg_properties.GetAuthProtos()
            noproxy = self.dlg_properties.GetIngnoreProxy()
            if useauth:
                useauth = [u for u in useauth if u in protos]
                logging.info('Applying authentication for {}'
                             .format(', '.join(useauth)))
            if noproxy:
                logging.info('Ignoring hosts: {}'.format(', '.join(noproxy)))
        else:
            user = pwd = useauth = None
            noproxy = backend.get_noproxy()

        # Start the working thread
        work = threading.Thread(target=self.DoApplyProxy,
                                args=(protos, hosts, ports, user, pwd, noproxy,
                                      useauth))
        work.start()

    def DoApplyProxy(self, protos, hosts, ports, user, pwd, noproxy, useauth):

        # Check before applying....
        checknames = ('bash', 'environment', 'apt', 'gsettings', 'sudoers')
        checkfuncs = (backend.check_bash, backend.check_environment,
                      backend.check_apt, backend.check_gsettings,
                      backend.check_sudoers)
        remfuncs = (backend.remove_bash, backend.remove_environment,
                    backend.remove_apt, backend.remove_gsettings,
                    backend.remove_sudoers)
        found = []
        remfound = {}
        for cfunc, name, rfunc in zip(checkfuncs, checknames, remfuncs):
            logging.info('Checking {}...'.format(name))
            result = cfunc()
            if result:
                found.extend(result)
                remfound[name] = rfunc

        # If found any settings, ask for overwrite
        if found:
            message = ('Proxy settings were detected in:\n{}'
                       .format('\n'.join(found)))
            logging.warning(message)
            warnbox = Synchronizer(wx.MessageBox,
                                   args=('Some proxy settings were detected '
                                         'in your system. Do you want to '
                                         'overwite them?', 'Confirm Overwrite'
                                         ),
                                   kwargs={'style': wx.CENTRE |
                                           wx.ICON_QUESTION | wx.YES_NO})
            overwrite = warnbox.run()
            if overwrite == wx.NO:
                logging.info('No settings were applied.')
                return
            else:
                logging.warning('Overwriting settings...')
                for name, rfunc in remfound.items():
                    logging.info('Removing {}...'.format(name))
                    rfunc()

        # Catch all the exceptions individually and report later
        errors = []
        try:
            logging.info('Setting bash...')
            backend.set_bash(protos, hosts, ports, user=user, pwd=pwd,
                             noproxy=noproxy, useauth=useauth)
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Setting environment...')
            backend.set_environment(protos, hosts, ports, user=user, pwd=pwd,
                                    noproxy=noproxy, useauth=useauth)
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Setting apt...')
            backend.set_apt(protos, hosts, ports, user=user, pwd=pwd,
                            useauth=useauth)
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Setting gsettings...')
            backend.set_gsettings(protos, hosts, ports, user=user, pwd=pwd,
                                  noproxy=noproxy)
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Setting sudoers...')
            backend.set_sudoers(protos, noproxy=noproxy)
        except Exception as e:
            errors.append(e)

        # Finalize
        if errors:
            errstring = '\n'.join((str(e) for e in errors))
            logging.error('The following errors occured while applying proxy '
                          'settings\n{}'.format(errstring))
        else:
            logging.info('Proxy settings were succesfully applied.')
            okbox = Synchronizer(wx.MessageBox,
                                 args=('Proxy settings were succesfully '
                                       'applied. You might have to restart '
                                       'your browser or any other '
                                       'applications for changes to take '
                                       'effect.', 'Settings Applied'),
                                 kwargs={'style': wx.OK})
            okbox.run()

    def OnUpdateDetails(self, details):
        # Check if the frame and it's attribute exist
        if self and self.tct_details:
            # The C++ object might get deleted while callafter is called.
            try:
                wx.CallAfter(self.tct_details.AppendText, details)
            except wx.PyDeadObjectError as err:
                logging.debug('No more updates required: {}'.format(err))
        else:
            logging.debug('No more updates required: {}'.format(self))

    def OnToggleDetails(self, event):
        action = not self.tct_details.IsShown()
        self.tct_details.Show(action)
        self.btn_togdetails.SetLabel('Hide Details' if action else
                                     'Show Details')
        self.pnl_main.GetSizer().Fit(self)
        self.Layout()
        # Toggle event for log monitor
        self.lmevent.set() if action else self.lmevent.clear()

    def OnProperties(self, event):
        # Singleton properties dialog
        if self.dlg_properties:
            self.dlg_properties.Show()
        else:
            logging.debug('Creating properties')
            self.dlg_properties = PropDialog(self, title='Properties')
            self.dlg_properties.Show()

    def OnRemoveProxy(self, event):
        logging.info('Removing proxy settings...')
        # Show warning (could implement backup facility)
        remove = wx.MessageBox('Are you sure you want to remove proxy '
                               'settings?', 'Confirm Overwrite',
                               style=wx.CENTRE | wx.ICON_QUESTION | wx.YES_NO)
        if remove == wx.NO:
            logging.info('No settings were removed.')
            return
        else:
            logging.warning('Removing settings...')
            # Start the working thread
            work = threading.Thread(target=self.DoRemoveProxy)
            work.start()

    def DoRemoveProxy(self):
        errors = []
        try:
            logging.info('Removing bash...')
            backend.remove_bash()
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Removing environment...')
            backend.remove_environment()
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Removing apt...')
            backend.remove_apt()
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Removing gsettings...')
            backend.remove_gsettings()
        except Exception as e:
            errors.append(e)
        try:
            logging.info('Removing sudoers...')
            backend.remove_sudoers()
        except Exception as e:
            errors.append(e)

        # Finalize
        if errors:
            logging.error('The following errors occured while removing proxy '
                          'settings\n{}'.format('\n'.join(errors)))
        else:
            logging.info('Proxy settings were succesfully removed.')
            okbox = Synchronizer(wx.MessageBox,
                                 args=('Proxy settings were succesfully '
                                       'removed. You might have to restart '
                                       'your browser or any other '
                                       'applications for changes to take '
                                       'effect.', 'Settings Removed'),
                                 kwargs={'style': wx.OK})
            okbox.run()

    def OnSetFocus(self, event):
        field = event.GetEventObject()
        # Clear if value is unchaged
        if field.GetValue() == field.GetName():
            field.Clear()
        event.Skip()

    def OnKillFocus(self, event):
        field = event.GetEventObject()
        # Reset if value is empty
        if not field.GetValue():
            field.SetValue(field.GetName())
        event.Skip()

    def OnAbout(self, event):
        info = wx.AboutDialogInfo()
        app = wx.GetApp()
        info.SetName(app.GetName())
        info.SetVersion(app.GetVersion())
        info.SetCopyright(app.GetCopyright())
        info.SetDescription(app.GetDescription())
        info.SetDevelopers(app.GetDevelopers())
        with open('gpl-3.0.txt', 'r') as lic:
            license = lic.read()
        info.SetLicense(license)
        wx.AboutBox(info)

    def OnClose(self, event):
        logging.info('Closing window...')
        event.Skip()

    def DoLayout(self):
        sizer_0 = wx.BoxSizer(wx.VERTICAL)
        sizer_00 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_000 = wx.StaticBoxSizer(self.stb_proxset, wx.VERTICAL)
        sizer_0000 = wx.GridBagSizer(vgap=5, hgap=5)
        sizer_001 = wx.BoxSizer(wx.VERTICAL)

        # Some preset styles
        style_1 = wx.ALIGN_CENTRE_VERTICAL | wx.ALIGN_LEFT
        style_2 = wx.BOTTOM | wx.EXPAND

        # Adding proxy settings widgets to a grid
        sizer_0000.Add(self.stt_http, (0, 0), (1, 1), style_1)
        sizer_0000.Add(self.tct_hosthttp, (0, 1), (1, 20), wx.EXPAND)
        sizer_0000.Add(self.tct_porthttp, (0, 21), (1, 1), wx.EXPAND)
        sizer_0000.Add(self.stt_https, (1, 0), (1, 1), style_1)
        sizer_0000.Add(self.tct_hosthttps, (1, 1), (1, 20), wx.EXPAND)
        sizer_0000.Add(self.tct_porthttps, (1, 21), (1, 1), wx.EXPAND)
        sizer_0000.Add(self.stt_ftp, (2, 0), (1, 1), style_1)
        sizer_0000.Add(self.tct_hostftp, (2, 1), (1, 20), wx.EXPAND)
        sizer_0000.Add(self.tct_portftp, (2, 21), (1, 1), wx.EXPAND)
        sizer_0000.Add(self.stt_socks, (3, 0), (1, 1), style_1)
        sizer_0000.Add(self.tct_hostsocks, (3, 1), (1, 20), wx.EXPAND)
        sizer_0000.Add(self.tct_portsocks, (3, 21), (1, 1), wx.EXPAND)
        sizer_000.Add(sizer_0000, 1, wx.ALL, 5)

        # Add all the buttons to a vertical sizer
        sizer_001.AddMany([(self.btn_applyprox, 0, style_2, 5),
                           (self.btn_removeprox, 0, style_2, 5),
                           (self.btn_properties, 0, style_2, 5),
                           (self.btn_about, 0, style_2, 5),
                           ((5,5), 1, wx.EXPAND),
                           (self.btn_togdetails, 0, style_2)])

        sizer_00.AddMany([(sizer_000, 1, wx.RIGHT, 10),
                          (sizer_001, 0, wx.EXPAND)])

        # Add everything to the outer most sizer
        sizer_0.Add(sizer_00, 1, wx.ALL | wx.ALIGN_CENTRE, 10)
        sizer_0.Add(self.tct_details, 1, wx.ALL ^ wx.TOP | wx.EXPAND, 10)

        self.pnl_main.SetSizer(sizer_0)
        sizer_0.Fit(self)
        self.Layout()
