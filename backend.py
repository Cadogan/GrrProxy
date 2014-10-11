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


"""
Proxy related backend operations.

This module provides functions for checking, applying and removing proxy
settings for Linux based operating systems. Some distributions of Linux might
require additional changes for proxy settings to work.

This module makes no effort in catching exceptions that might result from IO
related operations. Existance of a file is verified before opening it in all
cases (except when it is created). Some of the files modified here are very
sensitive. Setting wrong file permissions, file-modes or newline characters
could result in errors. Any changes made to these files must comply with the
underlying OS specifications.

All the strings in this module (except docstrings) uses single quotes for
uniformity. Any single quotes within them are escaped appropriately.
"""


import os
import subprocess


DEFAULT_PORT = 8080


# Root's files
environment = '/etc/environment'
bashbashrc = '/etc/bash.bashrc'
aptconf = '/etc/apt/apt.conf'
aptconfd = '/etc/apt/apt.conf.d'
aptfrag = os.path.join(aptconfd, '99proxy')
sudoers = '/etc/sudoers'
sudoersd = '/etc/sudoers.d'
sudodproxy = os.path.join(sudoersd, 'proxy')
profile = '/etc/profile'
profiled = '/etc/profile.d'
profdproxy = os.path.join(profiled, 'proxy.sh')

# User's files
home = os.getenv('HOME')
bashrc = os.path.join(home, '.bashrc')
bashprofile = os.path.join(home, '.bash_profile')
bashlogin = os.path.join(home, '.bash_login')
userprofile = os.path.join(home, '.profile')
bashenv = os.path.join(home, '.bash_env')


def get_noproxy():
    """
    Return default noproxy hosts from gsettings.
    """
    args = ['gsettings', 'get', 'org.gnome.system.proxy', 'ignore-hosts']
    # Assume gsettings uses single rather than double quotes
    noprolist = subprocess.check_output(args).split('\'')[1:-1:2]
    return noprolist


def find_phrase(filename, *phrases):
    """
    Return True if any of the phrases are in the file.
    """
    if not os.path.exists(filename):
        return

    with open(filename, 'r') as fil:
        lines = fil.readlines()
        for phrase in phrases:
            if any(phrase in l for l in lines):
                return True


def check_bash():
    """
    Return filename(s) containing proxy settings for bash.
    """
    checkfiles = [bashprofile, bashlogin, userprofile, bashenv,
                  bashbashrc, bashrc, profdproxy, profile]
    found = []
    for filename in checkfiles:
        if find_phrase(filename, '_proxy=', '_PROXY='):
            found.append(filename)
    return found


def check_environment():
    """
    Return filename(s) containing proxy settings for environment.
    """
    found = []
    if find_phrase(environment, '_proxy=', '_PROXY='):
        found.append(environment)
    return found


def check_apt():
    """Return filename(s) containing proxy settings for apt."""
    found = []
    checkfiles = [aptconf, aptfrag]
    for filename in checkfiles:
        if find_phrase(filename, '::proxy'):
            found.append(filename)
    return found


def check_gsettings():
    """
    Return non empty value(s) of proxy keys in GSettings.

    Some keys should neither be used nor modified. They cannot be relied for
    correct proxy settings either. You may filter them manually for further
    processing.
    """
    found = []
    args = ['gsettings', 'list-recursively', 'org.gnome.system.proxy']
    lines = subprocess.check_output(args).split('\n')
    for line in lines:
        # Check the last part
        if line and line.split()[-1] not in ('mode' 'true', 'false',
                                             '\'\'', '""'):
            found.append(line)
    return found


def check_sudoers():
    """
    Return filename(s) containing proxy settings for sudoers.
    """
    found = []
    checkfiles = [sudoers, sudodproxy]
    for filename in checkfiles:
        if find_phrase(filename, '_proxy', '_PROXY'):
            found.append(filename)
    return found


def set_bash(protos, hosts, ports, user=None, pwd=None,
             noproxy=None, useauth=None):
    """
    Apply proxy settings for bash.

    Bash reads and executes commands from files found at several locations.
    Some of these files takes precedence over the others. This also depends on
    wheather or not bash is invoked as an login shell.

    For more information, please refer to http://www.gnu.org/software/bash/
    manual/bashref.html#Bash-Startup-Files
    """
    # Check for profile.d reference in profile
    if not os.path.exists(profile):
        open(profile, 'w').close()
    with open(profile, 'r+') as prof:
        lines = prof.readlines()
        for line in lines:
            if os.path.join(profiled, '*.sh') in line:
                break
        # Line is absent, write the script
        else:
            script = ['if [ -d /etc/profile.d ]; then',
                      '  for i in /etc/profile.d/*.sh; do',
                      '    if [ -r $i ]; then',
                      '      . $i',
                      '    fi',
                      '  done',
                      '  unset i',
                      'fi']
            newline = '' if lines and lines[-1] == '\n' else '\n'
            prof.write('{}{}\n'.format(newline, '\n'.join(script)))

    # Ensure profile.d exists
    if not os.path.exists(profiled):
        os.makedirs(profiled)

    # Make or pick the superior file
    for filename in (bashprofile, bashlogin, userprofile):
        if os.path.exists(filename):
            supfile = filename
            break
    else:
        os.makedirs(bashprofile)
        supfile = bashprofile

    # Make the command lines
    lines = []
    authform = '{}:{}@'.format(user, pwd) if (user and pwd) else ''
    for proto, host, port in zip(protos, hosts, ports):
        # Use authentication for specified protocols
        auth = '' if useauth and proto not in useauth else authform
        # Make upper and lower cases spearately
        lines.append('export {0}_proxy="{0}://{3}{1}:{2}/"'
                     .format(proto, host, port, auth))
        lines.append('export {4}_PROXY="{0}://{3}{1}:{2}/"'
                     .format(proto, host, port, auth, proto.upper()))
    if noproxy:
        noproxy = ','.join(noproxy)
        lines.append('export no_proxy="{}"'.format(noproxy))
        lines.append('export NO_PROXY="{}"'.format(noproxy))

    # Write the lines
    contents = '\n'.join(lines)
    for filename in (profdproxy, supfile, bashbashrc, bashrc, bashenv):
        with open(filename, 'a+') as fil:
            lines = fil.readlines()
            newline = '' if lines and lines[-1] == '\n' else '\n'
            # Add ~/.bash_env to all files except to itself
            if filename == bashenv or any('BASH_ENV' in l for l in lines):
                beline = ''
            else:
                beline = 'export BASH_ENV="{}"\n'.format(bashenv)
            fil.write('{}{}{}\n'.format(newline, beline, contents))


def set_environment(protos, hosts, ports, user=None, pwd=None,
                    noproxy=None, useauth=None):
    """
    Apply proxy settings for environment.

    This file is read on login, when the PAM stack is activated. Changes will
    be visible after logging out and back in. You can check the programs using
    /etc/enviroment with:
    grep -l pam_env /etc/pam.d/*.
    """
    # Make the command lines
    lines = []
    authform = '{}:{}@'.format(user, pwd) if (user and pwd) else ''
    for proto, host, port in zip(protos, hosts, ports):
        # Use authentication for specified protocols
        auth = '' if useauth and proto not in useauth else authform
        # Make upper and lower cases spearately
        lines.append('{0}_proxy="{0}://{3}{1}:{2}/"'
                     .format(proto, host, port, auth))
        lines.append('{4}_PROXY="{0}://{3}{1}:{2}/"'
                     .format(proto, host, port, auth, proto.upper()))
    if noproxy:
        lines.append('no_proxy="{}"'.format(','.join(noproxy)))
        lines.append('NO_PROXY="{}"'.format(','.join(noproxy)))

    # Write the lines
    with open(environment, 'a+') as env:
        envlines = env.readlines()
        newline = '' if envlines and envlines[-1] == '\n' else '\n'
        # Add ~/.bash_env
        if any('BASH_ENV' in l for l in envlines):
            beline = ''
        else:
            beline = 'BASH_ENV="{}"\n'.format(bashenv)
        env.write('{}{}{}\n'.format(newline, beline, '\n'.join(lines)))


def set_apt(protos, hosts, ports, user=None, pwd=None, useauth=None):
    """
    Apply proxy settings for apt.
    """
    # Ensure aptconf.d is present
    if not os.path.exists(aptconfd):
        os.makedirs(aptconfd)

    # Make the command lines
    lines = []
    authform = '{}:{}@'.format(user, pwd) if (user and pwd) else ''
    for proto, host, port in zip(protos, hosts, ports):
        # Use authentication for specified protocols
        auth = '' if useauth and proto not in useauth else authform
        lines.append('Acquire::{0}::proxy "{0}://{3}{1}:{2}/";'
                     .format(proto, host, port, auth))

    # Write the lines
    with open(aptfrag, 'w') as frag:
        frag.write('\n{}\n'.format('\n'.join(lines)))


def set_gsettings(protos, hosts, ports, user=None, pwd=None,
                  noproxy=None):
    """
    Apply proxy settings for GSettings.
    """
    # Make the command lines
    cmds = ['gsettings set org.gnome.system.proxy mode \'manual\'']
    for proto, host, port in zip(protos, hosts, ports):
        cmds.append('gsettings set org.gnome.system.proxy.{} host \'{}\''
                    .format(proto, host))
        cmds.append('gsettings set org.gnome.system.proxy.{} port {}'
                    .format(proto, port))
    if user and pwd:
        # Use authentication for http (other's don't work)
        cmds.append('gsettings set org.gnome.system.proxy.http '
                    'use-authentication true')
        cmds.append('gsettings set org.gnome.system.proxy.http '
                    'authentication-user \'{}\''.format(user))
        cmds.append('gsettings set org.gnome.system.proxy.http '
                    'authentication-password \'{}\''.format(pwd))
    else:
        cmds.append('gsettings set org.gnome.system.proxy.http '
                    'use-authentication false')
    if noproxy:
        ighosts = ['\'{}\''.format(host) for host in noproxy]
        cmds.append('gsettings set org.gnome.system.proxy ignore-hosts "[{}]"'
                    .format(', '.join(ighosts)))

    # Call commands
    for cmd in cmds:
        subprocess.call(cmd, shell=True)


def set_sudoers(protos, noproxy=None):
    """
    Apply proxy settings for GSettings.

    CAUTION!
    A reference line to sudoers.d will be appended to the sudoers file if it
    couldn't be found. Every proxy values are written in a separate file inside
    sudoers.d. Any errors occured while editing these files could result in
    sudo denying you further access.
    """
    # Check for sudoers.d reference in sudoers file
    if not os.path.exists(sudoers):
        open(sudoers, 'w').close()
    with open(sudoers, 'r+') as sd:
        lines = sd.readlines()
        incdir = '#includedir'
        for line in lines:
            if incdir in line and sudoersd in line:
                break
        else:
            # Line is absent, write it in a new line
            newline = '' if lines and lines[-1] == '\n' else '\n'
            sd.write('{}{} {}\n'.format(newline, incdir, sudoersd))

    # Ensure sudoers.d is present
    if not os.path.exists(sudoersd):
        os.makedirs(sudoersd)

    # Make the variables (both cases)
    variables = ['{}_proxy {}_PROXY'.format(p, p.upper()) for p in protos]
    if noproxy:
        variables.extend(['no_proxy NO_PROXY'])

    # Write the variables
    fd = os.open(sudodproxy, os.O_WRONLY | os.O_CREAT, 0o440)
    with os.fdopen(fd, 'w') as sdp:
        sdp.write('\nDefaults env_keep += "{}"\n'
                  .format(' '.join(variables)))


def remove_lines(filename, *phrases):
    """
    Remove lines from the file containing any of the phrases.
    """
    if not os.path.exists(filename):
        return

    # Make new lines excluding the phrases
    newlines = []
    with open(filename, 'r') as fil:
        oldlines = fil.readlines()
        for line in oldlines:
            if not any(p in line for p in phrases):
                newlines.append(line)

    # Manage newline characters
    while len(newlines) > 1 and newlines[-1] == newlines[-2] == '\n':
        newlines.pop()
    if not newlines[-1].endswith('\n'):
        newlines.append('\n')

    # Write the new lines
    with open(filename, 'w') as fil:
        fil.write(''.join(newlines))


def remove_bash():
    """
    Remove proxy settings for bash.
    """
    for filename in check_bash():
        remove_lines(filename, '_proxy=', '_PROXY=')

    # Remove the proxy file inside profile.d
    if os.path.exists(profdproxy):
        os.remove(profdproxy)


def remove_environment():
    """
    Remove proxy settings for environment.
    """
    for filename in check_environment():
        remove_lines(filename, '_proxy=', '_PROXY=')


def remove_apt():
    """
    Remove proxy settings for apt.
    """
    for filename in check_apt():
        remove_lines(aptconf, '::proxy')

    # Remove the proxy file inside aptconf.d
    if os.path.exists(aptfrag):
        os.remove(aptfrag)


def remove_gsettings():
    """
    Remove proxy settings for GSettings.
    """
    args = ['gsettings', 'reset-recursively', 'org.gnome.system.proxy']
    subprocess.call(args)


def remove_sudoers(filenames=None):
    """
    Remove proxy settings for sudo.
    """
    for filename in check_sudoers():
        remove_lines(sudoers, '_proxy', '_PROXY')

    # Remove the proxy file inside sudoers.d
    if os.path.exists(sudodproxy):
        os.remove(sudodproxy)
