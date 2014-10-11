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
import wx

import backend


class PropDialog(wx.Dialog):

    def __init__(self, *args, **kwargs):
        super(PropDialog, self).__init__(*args, **kwargs)

        # widgets
        self.stb_auth = wx.StaticBox(self, label='Authentication')
        self.chk_useauth = wx.CheckBox(self, label="Use authentication")
        self.tct_username = wx.TextCtrl(self, name='username')
        self.tct_password = wx.TextCtrl(self, name='password',
                                        style=wx.TE_PASSWORD)
        self.stt_auth = wx.StaticText(self, label='Use authentication for:')
        self.chk_http = wx.CheckBox(self, label='http')
        self.chk_https = wx.CheckBox(self, label='https')
        self.chk_ftp = wx.CheckBox(self, label='ftp')
        self.chk_socks = wx.CheckBox(self, label='socks')
        self.stt_igproxy = wx.StaticText(self, label='Ignore proxy for hosts:')
        self.tct_igproxy = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_ok = wx.Button(self, wx.ID_OK)

        self.wid_authtexts = (self.tct_username, self.tct_password)
        self.wid_authchecks = (self.chk_http, self.chk_https,
                               self.chk_ftp, self.chk_socks)

        self.stt_auth.Disable()
        for widget in self.wid_authchecks:
            widget.SetValue(True)
            widget.Disable()

        ighosts = backend.get_noproxy()
        self.tct_igproxy.AppendText('\n'.join(ighosts))

        for widget in self.wid_authtexts:
            widget.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
            widget.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
            widget.SetValue(widget.GetName())
            widget.Disable()
        self.Bind(wx.EVT_CHECKBOX, self.OnUseAuth, self.chk_useauth)

        self.DoLayout()

    def OnUseAuth(self, event):
        # Toggle authentication widgets
        action = event.GetEventObject().GetValue()
        for widget in itertools.chain(self.wid_authtexts, self.wid_authchecks):
            widget.Enable(action)
        self.stt_auth.Enable(action)

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

    def GetAuthTexts(self):
        if self.chk_useauth.GetValue():
            authtexts = [w.GetValue() for w in self.wid_authtexts]
            return authtexts

    def GetAuthProtos(self):
        if self.chk_useauth.GetValue():
            authprotos = [w.GetLabel() for w in self.wid_authchecks
                          if w.GetValue()]
            return authprotos

    def GetIngnoreProxy(self):
        noproxy = self.tct_igproxy.GetValue().split()
        return noproxy if noproxy else None

    def DoLayout(self):
        sizer_0 = wx.BoxSizer(wx.VERTICAL)
        sizer_00 = wx.StaticBoxSizer(self.stb_auth, wx.VERTICAL)
        sizer_000 = wx.GridBagSizer(vgap=5, hgap=5)
        sizer_01 = wx.BoxSizer(wx.HORIZONTAL)

        sizer_000.Add(self.chk_useauth, (0, 0))
        sizer_000.Add(self.tct_username, (1, 0), (1, 3), wx.EXPAND)
        sizer_000.Add(self.tct_password, (2, 0), (1, 3), wx.EXPAND)
        sizer_000.Add(self.stt_auth, (3, 0))
        sizer_000.Add(self.chk_http, (4, 0))
        sizer_000.Add(self.chk_https, (4, 1))
        sizer_000.Add(self.chk_ftp, (5, 0))
        sizer_000.Add(self.chk_socks, (5, 1))
        sizer_00.Add(sizer_000, 1, wx.ALL, 5)

        sizer_01.Add(self.btn_cancel)
        sizer_01.Add(self.btn_ok, 0, wx.LEFT, 5)

        sizer_0.Add(sizer_00, 0, wx.ALL, 10)
        sizer_0.Add(self.stt_igproxy, 0, wx.ALL, 10)
        sizer_0.Add(self.tct_igproxy, 0, wx.ALL ^ wx.TOP | wx.EXPAND, 10)
        sizer_0.Add(sizer_01, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        self.SetSizer(sizer_0)
        sizer_0.Fit(self)
        self.Layout()
