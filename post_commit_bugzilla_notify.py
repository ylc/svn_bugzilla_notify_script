#!/usr/bin/env python

# Script to update bugzilla based on svn commit log message. 
# This assumes that email_in.pl is set up to monitor the To: address. 
#
# To use, customize the variables to_addr, from_addr and view_svn_url and 
# call this script from your post_commit_hook by adding the following line:
#
# /path/to/svn/hooks/post_commit_bugzilla_notify.py "$REPOS" "$REV"
#
# It is  possible for the user  to specify a bug  id (or multiple  id's) and a
# "command" which is used to  share information with bugzilla. For example, if
# a user  writes in his commit  message "... ..  fixes bug 123 and  refers bug
# 456... ..."  then a  summary of the  commit will  be posted to  the bugzilla
# pages of bug 123  and bug 456. Also, assuming that bug  123 is open, it will
# be marked  as RESOLVED/FIXED. It is  also possible to specify  in the commit
# log "reopens bug 123" and the  commit summary will be posted to bugzilla and
# the bug 123 will be reopened (assuming a closed state).
#
# This script is based on the trac-post-commit-hook by Stephen Hansen
#
# Copyright (c) 2009 Yogesh Chobe
#
# ----------------------------------------------------------------------------
# Copyright (c) 2004 Stephen Hansen 
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software. 
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
# ----------------------------------------------------------------------------

import sys
import subprocess
import os
import smtplib
import re

to_addr = "BUGZILLA_INCOMING@YOUR_BUGZILLA_SERVER.com"
from_addr = "svncommit@YOUR_BUGZILLA_SERVER.com" 
view_svn_url = "http://VIEW_SVN_URL_UP_TO_path=/PROJECT/PATH/"


def add_status( ref ):
    if ref == "Fixed":
        return "@bug_status = RESOLVED\n@resolution = FIXED\n\n"
    elif ref == "Reopens":
        return "@bug_status = REOPENED\n\n"
    else:
        return "\n"


def notify_bugzilla_from_svn( repo, rev ):

    supported_cmds = {'fix':        'Fixed',
                      'fixed':      'Fixed',
                      'fixes':      'Fixed',
                      'addresses':  'Refers',
                      're':         'Refers',
                      'references': 'Refers',
                      'refs':       'Refers',
                      'refer':      'Refers',
                      'refers':     'Refers',
                      'reopens':    'Reopens',
                      'reopen':     'Reopens'}

    #get info about commit
    svn_proc = subprocess.Popen("/usr/bin/svnlook info %s -r %s" % ( repo, rev ), shell=True, \
                                    stdout = subprocess.PIPE, env = os.environ)
    svn_info = [line for line in svn_proc.stdout.readlines()]

    #site-specific: format it for bugzilla display
    svn_info.insert(0 , "New Revision: %s     Author: " % rev)
    svn_info[3] = "\nLog:\n"
    svn_info = ''.join( svn_info )

    #build re to look for reference to a bug
    bug_prefix = '(?:#|(?:Bug|Bug:|bug|bug:|BUG|BUG:)[: ]?)'
    bug_reference = bug_prefix + '[0-9]+'
    bug_command =  (r'(?P<action>[A-Za-z]*).?'
                       '(?P<ticket>%s(?:(?:[, &]*|[ ]?and[ ]?)%s)*)' %
                       (bug_reference, bug_reference))
    command_re = re.compile(bug_command)
    bug_re = re.compile(bug_prefix + '([0-9]+)')

    #find all references to bugzilla bugs
    cmd_groups = command_re.findall(svn_info)

    s = smtplib.SMTP("localhost")

    for command, bugs in cmd_groups:
        bug_id = bug_re.findall(bugs)[0]
        action = supported_cmds.get(command.lower(),'')
        if action:
            msg = "From: %s\nTo: %s\nSubject: [Bug %s]\n" % ( from_addr, to_addr, bug_id )
            msg += add_status( action )
            msg += svn_info 
            msg += "\nChanges:\n"
            svn_proc = subprocess.Popen("/usr/bin/svnlook changed %s -r %s" % ( repo, rev ), shell=True, \
                                    stdout = subprocess.PIPE, env = os.environ)
            msg += ''.join(svn_proc.stdout.readlines())
            msg += "Patch:\n"
            msg+= "%s&rev=%s&oldrev=%s\n"\
                % ( view_svn_url, rev, str ( int ( rev ) - 1 ) )

            s.sendmail(from_addr, to_addr, msg)
    
    s.quit()


def main():
    if len( sys.argv ) != 3:
        print """Please call script with two args"""
        sys.exit( 1 )
    notify_bugzilla_from_svn( sys.argv[1], sys.argv[2] )

if __name__ == '__main__': main()
