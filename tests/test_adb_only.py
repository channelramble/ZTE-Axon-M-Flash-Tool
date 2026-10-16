"""Offline tests for the TWRP diagnostic MTP startup policy."""
import gzip
import json
import subprocess
import sys
import unittest

import test_fujisan_image as fixtures
from test_fujisan_image import SCRIPT, boot_payload, cpio_file, image, ramdisk


def usb_ramdisk(configfs, extra_action=b"", recovery=b"mtp.crash_check\0tw_mtp_enabled\0"):
    """Small authored fixtures for both supported TWRP USB startup paths."""
    init = b"on fs\n    mount functionfs adb /dev/usb-ffs/adb uid=2000,gid=2000\n" + image.CHARGER_PATCH
    props = b"ro.debuggable=1\npersist.sys.usb.config=adb\n"
    if configfs:
        usb = b"""on early-init
    mount configfs none /config
    mkdir /config/usb_gadget/g1/functions/ffs.adb 0770 root shell
    mkdir /config/usb_gadget/g1/functions/mtp.gs0 0770 root shell

on boot
    setprop sys.usb.config none
    setprop sys.usb.config adb

on property:sys.usb.config=none && property:sys.usb.configfs=1
    write /config/usb_gadget/g1/UDC none
    stop adbd
    setprop sys.usb.ffs.ready 0

on property:sys.usb.config=adb && property:sys.usb.configfs=1
    start adbd

on property:sys.usb.ffs.ready=1 && property:sys.usb.config=adb && property:sys.usb.configfs=1
    symlink /config/usb_gadget/g1/functions/ffs.adb /config/usb_gadget/g1/configs/b.1/f1
    write /config/usb_gadget/g1/UDC ${sys.usb.controller}
    setprop sys.usb.state adb

on property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1
    start adbd

on property:sys.usb.ffs.ready=1 && property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1
    symlink /config/usb_gadget/g1/functions/mtp.gs0 /config/usb_gadget/g1/configs/b.1/f1
    write /config/usb_gadget/g1/UDC ${sys.usb.controller}
    setprop sys.usb.state mtp,adb

"""
    else:
        props += b"persist.sys.usb.config=mtp,adb\n"
        usb = b"""on fs
    write /sys/class/android_usb/android0/functions adb
    setprop sys.usb.config ${persist.sys.usb.config}

on property:sys.usb.config=none
    stop adbd
    write /sys/class/android_usb/android0/enable 0

on property:sys.usb.config=adb
    write /sys/class/android_usb/android0/functions ${sys.usb.config}
    start adbd
    setprop sys.usb.state ${sys.usb.config}

on property:sys.usb.config=mtp
    write /sys/class/android_usb/android0/functions ${sys.usb.config}
    write /sys/class/android_usb/android0/enable 1

on property:sys.usb.config=mtp,adb
    write /sys/class/android_usb/android0/functions ${sys.usb.config}
    write /sys/class/android_usb/android0/enable 1

on property:sys.usb.config=mass_storage,adb
    write /sys/class/android_usb/android0/functions ${sys.usb.config}

"""
    records = [('init.rc', init), ('default.prop', b'prop.default'),
               ('prop.default', props), ('init.recovery.usb.rc', usb + extra_action),
               ('sbin/recovery', recovery), ('TRAILER!!!', b'')]
    return gzip.compress(b''.join(cpio_file(name, data, mode=0o120777 if name == 'default.prop' else 0o100644,
                                            inode=index + 1)
                                  for index, (name, data) in enumerate(records)), mtime=0)


def archive(ramdisk):
    return {entry[0]: entry for entry in image.cpio_entries(gzip.decompress(ramdisk))}


class AdbOnlyTests(unittest.TestCase):
    def test_preserves_charger_adb_actions_and_other_records(self):
        for configfs in (False, True):
            with self.subTest(configfs=configfs):
                original = usb_ramdisk(configfs)
                patched = image.patch_adb_only(original)
                old, new = archive(original), archive(patched)
                self.assertEqual(set(old), set(new))
                self.assertEqual([name for name in old if old[name] != new[name]],
                                 ['prop.default', 'init.recovery.usb.rc'])
                for name in ('prop.default', 'init.recovery.usb.rc'):
                    self.assertEqual(old[name][1][:6], new[name][1][:6])
                props, usb = new['prop.default'][2], new['init.recovery.usb.rc'][2]
                self.assertIn(b'mtp.crash_check=1\n', props)
                self.assertNotIn(b'persist.sys.usb.config=mtp', props)
                self.assertNotIn(b'functions/mtp.', usb)
                self.assertNotIn(b'sys.usb.state mtp', usb)
                for action in old['init.recovery.usb.rc'][2].split(b'\non '):
                    header = action.split(b'\n', 1)[0]
                    if b'property:sys.usb.config=adb' in header or b'property:sys.usb.config=none' in header:
                        if not configfs:
                            action = action.replace(b'functions ${sys.usb.config}', b'functions adb')
                        self.assertIn(action.rstrip(b'\n'), usb)
                self.assertEqual(image.patch_adb_only(patched), patched)
                if not configfs:
                    self.assertNotIn(b'setprop sys.usb.config ${persist.sys.usb.config}', usb)
                    self.assertNotIn(b'functions ${sys.usb.config}', usb)
                    self.assertIn(b'functions mass_storage,adb\n', usb)

    def test_mtp_requests_cannot_activate_hardware_actions(self):
        for configfs in (False, True):
            usb = archive(image.patch_adb_only(usb_ramdisk(configfs)))['init.recovery.usb.rc'][2]
            actions = usb.split(b'\non ')
            mtp_actions = [action for action in actions
                           if b'property:sys.usb.config=mtp' in action.split(b'\n', 1)[0]]
            self.assertEqual(len(mtp_actions), 2)
            for action in mtp_actions:
                self.assertEqual(action.split(b'\n', 1)[1].strip(), b'setprop sys.usb.config adb')

    def test_unknown_or_missing_startup_paths_rejected(self):
        with self.assertRaisesRegex(ValueError, 'known TWRP'):
            image.patch_adb_only(usb_ramdisk(True, recovery=b'not TWRP'))
        with self.assertRaisesRegex(ValueError, 'expected prop.default'):
            image.patch_adb_only(ramdisk())
        extra = b'on property:sys.usb.config=mtp,adb && property:unexpected=1\n    start unexpected\n'
        with self.assertRaisesRegex(ValueError, 'unexpected MTP init actions'):
            image.patch_adb_only(usb_ramdisk(True, extra_action=extra))
        extra = b'on property:unexpected=1\n    write /unreviewed/functions mtp\n'
        with self.assertRaisesRegex(ValueError, 'unhandled MTP'):
            image.patch_adb_only(usb_ramdisk(False, extra_action=extra))
        extra = b'on property:unexpected=1\n    write /sys/class/android_usb/android0/functions ${sys.usb.config}\n'
        with self.assertRaisesRegex(ValueError, 'unreviewed dynamic'):
            image.patch_adb_only(usb_ramdisk(False, extra_action=extra))

    def test_conflicting_prepatched_state_rejected(self):
        patched = image.patch_adb_only(usb_ramdisk(True))
        for old, new in ((b'mtp.crash_check=1', b'mtp.crash_check=0'),
                         (b'persist.sys.usb.config=adb', b'persist.sys.usb.config=mtp,adb')):
            records = []
            for name, fields, content, encoded in image.cpio_entries(gzip.decompress(patched)):
                if name == 'prop.default':
                    encoded = cpio_file(name, content.replace(old, new))
                records.append(encoded)
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'conflicting adb-only'):
                image.patch_adb_only(gzip.compress(b''.join(records)))


class AdbOnlySigningTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.SigningTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.SigningTests.tearDownClass.__func__)

    def test_cli_combines_with_charger_and_preserves_kernel(self):
        source = self.directory / 'usb-source.img'
        output = self.directory / 'usb-adb-only.img'
        boot = image.BootImage(boot_payload())
        payload = boot.rebuild(ramdisk=usb_ramdisk(True))
        source.write_bytes(image.sign_image(payload, '/boot', self.key, self.cert))
        proc = subprocess.run([sys.executable, str(SCRIPT), 'patch', str(source), str(output),
                               '--target', '/boot', '--key', str(self.key), '--certificate', str(self.cert),
                               '--charger', '--adb-only'], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = image.BootImage(output.read_bytes())
        self.assertEqual(result.kernel, boot.kernel)
        self.assertTrue(result.id_valid)
        image.verify_signature(result.payload, result.trailer)
        self.assertIn(b'mtp.crash_check=1', archive(result.ramdisk)['prop.default'][2])
        self.assertTrue(json.loads(output.with_suffix('.img.json').read_text())['changes']['adb_only'])


if __name__ == '__main__':
    unittest.main()
