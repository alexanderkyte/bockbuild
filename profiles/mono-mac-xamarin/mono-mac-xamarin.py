#!/usr/bin/python -B -u

import itertools
import os
import re
import shutil
import string
import sys
import tempfile

sys.path.append('../..')

from bockbuild.darwinprofile import DarwinProfile
from bockbuild.util.util import *
from glob import glob

sys.path.append('../mono-mac-release')

from MonoReleaseProfile import MonoReleaseProfile

class MonoXamarinPackageProfile(MonoReleaseProfile):
    def __init__(self):
        MonoReleaseProfile.__init__ (self)

        from packages.mono_master import MonoMasterPackage

        # add the private stuff
        found = False
        for idx, package in enumerate(self.packages):
            if package == 'mono_master':
                self.packages[idx] = 'mono_crypto'
                found = True
                break

        if not found:
            error ('Did not find "mono_master" package to remap')

        self.packages.append ('ms-test-suite')

        if self.unsafe:
            warn ('--unsafe option used, will not attempt to sign package!')
            return 

        self.identity = "Developer ID Installer: Xamarin Inc"

        output = backtick("security -v find-identity")
        if self.identity not in " ".join(output):
            error ("Identity '%s' was not found. You can create an unsigned package by adding '--unsafe' to your command line." % self.identity)

        password = os.getenv("CODESIGN_KEYCHAIN_PASSWORD")
        if password:
            print "Unlocking the keychain"
            run_shell ("security unlock-keychain -p %s" % password)
        else:
            error ("CODESIGN_KEYCHAIN_PASSWORD needs to be defined.")


    def run_pkgbuild(self, working_dir, package_type):
        output = MonoReleaseProfile.run_pkgbuild (self, working_dir, package_type)

        output_unsigned = output + '.UNSIGNED'
        shutil.move (output, output_unsigned)

        if self.unsafe:
            return output_unsigned

        productsign = "/usr/bin/productsign"
        productsign_cmd = ' '.join([productsign,
                                    "-s '%s'" % self.identity,
                                    "'%s'" % output_unsigned,
                                    "'%s'" % output])
        run_shell (productsign_cmd)
        os.remove(output_unsigned)
        self.verify_codesign (output)

        return output

    def verify_codesign(self, pkg):
        oldcwd = os.getcwd()
        try:
            name = os.path.basename(pkg)
            pkgdir = os.path.dirname(pkg)
            os.chdir(pkgdir)
            spctl = "/usr/sbin/spctl"
            spctl_cmd = ' '.join(
                [spctl, "-vvv", "--assess", "--type install", name, "2>&1"])
            output = backtick(spctl_cmd)

            if "accepted" in " ".join(output):
                warn ("%s IS SIGNED" % pkg)
            else:
                error ("%s IS NOT SIGNED:" % pkg)
        finally:
            os.chdir(oldcwd)

MonoXamarinPackageProfile().build()
