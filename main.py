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

import re, sys, os, argparse, socket, urllib2, time, base64
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
            print "Checking TCP Connection to %s:%s" % (monitor.get('host'), monitor.get('port'))
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((monitor.get('host'), int(monitor.get('port'))))
            s.shutdown(2)
        elif monitor.tag == 'udptest':
            print "Checking UCP Connection to %s:%s" % (monitor.get('host'), monitor.get('port'))
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((monitor.get('host'), int(monitor.get('port'))))
            s.shutdown(2)
        elif monitor.tag == 'urltest':
            print "Checking URL: %s" % (monitor.get('url'))
            request = urllib2.Request(monitor.get('url'))
            username = monitor.get('username', '')
            password = monitor.get('password', '')
            if len(username) > 0 and len(password) > 0:
                print "Using HTTP Basic Authentication"
                auth = base64.encodestring(
                        '%s:%s' % (username, password)).replace('\n', '')
                request.add_header("Authorization", "Basic %s" % auth)
            req = urllib2.urlopen(request)
            regex = monitor.get('regex', '')
            contains = monitor.get('contains', '')
            if len(regex) > 0 or len(contains) > 0:
                data = req.read()
                if len(regex) > 0:
                    self.assertNotNone(re.search(regex, data), "Regex not found: %s" % regex)
                if len(contains) > 0:
                    self.assertTrue(contains in data, "Substring not found: %s" % contains)
        elif monitor.tag == 'filetest':
            print "Checking File: %s" % (monitor.get('file'))
            regex = monitor.get('regex', '')
            contains = monitor.get('contains', '')
            minSize = monitor.get('minSize', '0')
            maxSize = monitor.get('maxSize', None)
            with open(monitor.get('file'), 'rb') as f:
                if len(regex) > 0 or len(contains) > 0 or minSize > 0 or maxSize is not None:
                    data = f.read()
                    print "Actual file size: %d bytes" % (len(data))
                    if len(regex) > 0:
                        self.assertNotNone(re.search(regex, data), "Regex not found: %s" % regex)
                    if len(contains) > 0:
                        self.assertTrue(contains in data, "Substring not found: %s" % contains)
                    if minSize > 0:
                        self.assertLessEqual(minSize, len(data), "File is smaller than %d bytes" % minSize)
                    if maxSize is not None:
                        self.assertGreaterEqual(maxSize, len(data), "File is larger than %d bytes" % maxSize)
            age = time.time() - os.path.getmtime(monitor.get('file'))
            print "Actual file age: %d seconds (%d days)" % (age, age / 86400)
            minAge = monitor.get('minAge', None)
            if minAge is not None:
                self.assertLessEqual(minAge, age, "File is younger than %d seconds" % minAge)
            maxAge = monitor.get('maxAge', None)
            if maxAge is not None:
                self.assertGreaterEqual(maxAge, age, "File is older than %d seconds" % maxAge)
        elif monitor.tag == 'nofiletest':
            try:
                open(monitor.get('file'), 'rb')
                self.fail("File exists and should not")
            except IOError:
                pass
        elif monitor.tag == 'disktest':
            if sys.platform.startswith("win"):
                import win32api
                freebytes = win32api.GetDiskFreeSpaceEx(monitor.get('disk'))[0]
            else:
                statvfs = os.statvfs(monitor.get('disk'))
                freebytes = statvfs.f_bsize * statvfs.f_bavail
            print "Actual free space: %d bytes (%d MB)" % (freebytes, freebytes / 1048576)
            minSize = monitor.get('minBytes', '0')
            maxSize = monitor.get('maxBytes', None)
            self.assertLessEqual(minSize, freebytes, "Disk has less than %d bytes available" % minSize)
            if maxSize is not None:
                self.assertGreaterEqual(maxSize, freebytes, "Disk has more than %d bytes available" % maxSize)
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

