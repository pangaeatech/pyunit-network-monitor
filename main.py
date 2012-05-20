# -.- coding: utf-8 -.-
# -.- dependencies: Python 2.5+ -.-

"""
PyUnit-based Port/Host Monitor

Copyright © 2012 Pangaea Information Technologies, Ltd.
                 http://www.pangaeatech.com/

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
  * Neither the name of Pangaea Information Technologies, nor the names of
    any contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
THE POSSIBILITY OF SUCH DAMAGE.
"""

import re, sys, os, argparse, socket, urllib2
from xml.etree import ElementTree
from lib import unittest, xmlrunner

__version__ = "0.1"

def _parse_commandline():
    """
    Generates a commandline parser for main()

    @rtype: argparse.ArgumentParser
    @return: the commandline parser
    """
    parser = argparse.ArgumentParser(version="%(prog)s v" + __version__,
        description="PyUnit-based Port/Host Monitor")

    parser.add_argument("--xml-dir", action="store", default=None,
                        dest="outdir", help="If specified, then output results as XML in this directory.  Otherwise, outputs results as TEXT to stdout")
    parser.add_argument("--config", action="store", default='config.xml',
                        dest="config", help="Use the specified file instead of config.xml")

    return parser

def create_tests(config_file):
    """
    Generates a TestCase instance containing one test method for each monitor
    defined in the config file.

    @param config_file: The XML configuration file defining the monitors
    @type config_file: string
    @rtype: unittest.TestCase
    @return: a subclass of unittest.TestCase containing the tests to run
    """
    tests = {'__class__': 'testclass'}

    testnum = 0
    for monitor in ElementTree.parse(config_file).getroot():
        name = re.sub('[^A-Za-z0-9]+', '_', monitor.get('name', monitor.tag)).strip('_')
        tests["test_%d_%s" % (testnum, name)] = create_test(monitor)
        testnum += 1

    if testnum <= 0:
        tests['test_no_tests'] = create_test(None)

    return type('testclass', (unittest.TestCase, object), tests)

def create_test(monitor):
    """
    Creates a test function for the given monitor definition

    @param monitor: The definition of the monitor to create a test case for (if
                    None, then create a test which just executes a self.fail()
    @type monitor: xml.etree.ElementTree.Element
    @rtype: function
    @return: a function to execute the specified monitor as a pyUnit test
    """
    def method(self):
        if monitor is None:
            self.fail("No valid monitor found")
        elif monitor.tag == 'tcptest':
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(monitor.get('host'), monitor.get('port'))
            s.shutdown(2)
        elif monitor.tag == 'udptest':
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(monitor.get('host'), monitor.get('port'))
            s.shutdown(2)
        elif monitor.tag == 'urltest':
            request = urllib2.Request(monitor.get('url'))
            username = monitor.get('username', '')
            password = monitor.get('password', '')
            if len(username) > 0 and len(password) > 0:
                auth = base64.encodestring(
                        '%s:%s' % (username, password)).replace('\n', '')
                request.add_header("Authorization", "Basic %s" % auth)
            req = urllib2.urlopen(request)
            regex = monitor.get('regex', '')
            if len(regex) > 0:
                self.assertNotNone(re.search(regex, req.read()))
        elif monitor.tag == 'filetest':
            regex = monitor.get('regex', '')
            minSize = monitor.get('minSize', '0')
            maxSize = monitor.get('maxSize', None)
            with open(monitor.get('file'), 'rb') as f:
                if len(regex) > 0 or minSize > 0 or maxSize is not None:
                    data = f.read()
                    if len(regex) > 0:
                        self.assertNotNone(re.search(regex, data))
                    if minSize > 0:
                        self.assertLessEqual(minSize, len(data))
                    if maxSize is not None:
                        self.assertGreaterEqual(maxSize, len(data))
        elif monitor.tag == 'nofiletest':
            try:
                open(monitor.get('file'), 'rb')
                self.fail("IOError Expected")
            except IOError:
                pass
        elif monitor.tag == 'disktest':
            if sys.platform.startswith("win"):
                import win32api
                freebytes = win32api.GetDiskFreeSpaceEx(monitor.get('disk'))[0]
            else:
                statvfs = os.statvfs(monitor.get('disk'))
                freebytes = statvfs.f_bsize * statvfs.f_bavail
            minSize = monitor.get('minBytes', '0')
            maxSize = monitor.get('maxBytes', None)
            self.assertLessEqual(minSize, freebytes)
            if maxSize is not None:
                self.assertGreaterEqual(maxSize, freebytes)
        else:
            self.fail("Unknown monitor type: " + monitor.tag)
    return method

def main(options):
    """
    Generate and run the unit tests based on the config file.
    """
    testclass = create_tests(options.config)
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(testclass))
    if options.outdir is not None:
        if not os.path.isdir(options.outdir):
            os.makedirs(options.outdir)
        runner = xmlrunner.XMLTestRunner()
        runner._path = options.outdir
    else:
        runner = unittest.TextTestRunner(verbosity=2)
    results = runner.run(suite)
    return len(results.failures) + len(results.errors)

if __name__ == '__main__':
    sys.exit(main(_parse_commandline().parse_args()))

