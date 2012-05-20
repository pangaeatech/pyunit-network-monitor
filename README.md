PyUnit-Based Network Monitor
----------------------------

This project grew out of our need to monitor critical IT infrastructure without
having to learn and manage a large monitoring system such as
[Nagios](http://www.nagios.org).  As a custom software development company, we
already utilize [Jenkins](http://jenkins-ci.org) to manage all of our builds, 
unit tests and documentation generation.  We decided to leverage that existing
infrastructure to create a monitoring tool that would work just like a set of 
unit tests.

The result of this effort is a PyUnit-Based Network Monitor.  To use this
monitor, modify the config.xml file to suit your needs and deploy the code to
Jenkins.  Using the "Build Periodically" trigger in Jenkins, you can
automatically run this monitor on any schedule you like.  Under the "Post-build
Actions" section, you can configure sending email for every failed build.  This
monitor supports formatting the output as JUnit-compatible reports, so you can
use the "Publish JUnit Test Result Report" functionality to have Jenkins track
your monitor results over time as well.

> Note: if you don't currently have Jenkins, but wish to use this network
> monitor, you can create a free hosted Jenkins instance at
> [OpenShift](https://openshift.redhat.com/app/) which supports python
> out-of-the-box.

Currently, this tool supports the following types of monitors:
* **urltest:** Test that a URL is valid and accessible.  Optionally, check the
  contents of the returned data against a substring and/or regular expression. 
  Supports various protocols (http, https, ftp, etc.) and supports basic HTTP
  authentication.
* **tcptest:** Test that a TCP port is open on a particular host
* **udptest:** Test that a UDP port is open on a particular host
* **filetest:** Test for the existence of a file in the filesystem.
  Optionally, check the contents of the file against a substring and/or regular 
  expression.  Additionally, you can assert a minimum and maximum byte size 
  on the file and/or a minimum and maximum modification time for the file.
* **nofiletest:** Test for the *non*-existence of a file in the filesystem.
* **disktest:** Test the amount of free space on a disk/partition.  Under
  Windows, network disks are supported using 
  [UNC notation](http://en.wikipedia.org/wiki/Path_%28computing%29) (Note: you
  must have the [win32api](http://sourceforge.net/projects/pywin32/files/)
  extension installed to support this).

For more details on configuration, see the 
[config.xml schema](/blob/master/lib/config.xsd).  For details about how to
run the monitor, type `python main.py -h` to view the help content.

This software is released under the [Modified BSD License](http://en.wikipedia.org/wiki/BSD_licenses).
