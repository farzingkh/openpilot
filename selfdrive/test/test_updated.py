#!/usr/bin/env python3
import os
import tempfile
import unittest
import signal
import subprocess
import time

from common.basedir import BASEDIR
from common.params import Params


class TestUpdater(unittest.TestCase):

  def setUp(self):
    self.updater_proc = None

    try:
      os.remove("/tmp/safe_staging_overlay.lock")
    except Exception:
      pass

    tmp_dir = tempfile.mkdtemp()
    org_dir = os.path.join(tmp_dir, "commaai")
    os.mkdir(org_dir)
    test_dir = org_dir

    self.basedir = tempfile.mkdtemp(dir=test_dir)
    self.git_remote_dir = tempfile.mkdtemp(dir=test_dir)
    self.staging_dir = tempfile.mkdtemp(dir=test_dir)

    submodules = subprocess.check_output("git submodule --quiet foreach 'echo $name'",
                                         shell=True, cwd=BASEDIR, encoding='utf8').split()
    # setup local submodule remotes
    for s in submodules:
      sub_path = os.path.join(org_dir, s.split("_repo")[0])
      self._run(f"git clone {s} {sub_path}.git", cwd=BASEDIR)

    # setup two git repos, a remote and one we'll run updated in
    self._run([
      f"git clone {BASEDIR} {self.git_remote_dir}",
      f"git clone {self.git_remote_dir} {self.basedir}",
      f"cd {self.basedir} && git submodule init && git submodule update",
      f"cd {self.basedir} && scons -j4 cereal"
    ])

    self.params = Params(db=os.path.join(self.basedir, "persist/params"))
    self.params.clear_all()

  def tearDown(self):
    if self.updater_proc is not None:
      self.updater_proc.terminate()
      self.updater_proc.wait(30)

  def _run(self, cmd, cwd=None):
    if not isinstance(cmd, list):
      cmd = (cmd,)

    for c in cmd:
      subprocess.check_output(c, cwd=cwd, shell=True)

  def _start_updater(self):
    os.environ["PYTHONPATH"] = self.basedir
    os.environ["UPDATER_TESTING"] = "1"
    os.environ["UPDATER_STAGING_ROOT"] = self.staging_dir
    updated_path = os.path.join(self.basedir, "selfdrive/updated.py")
    self.updater_proc = subprocess.Popen(updated_path, env=os.environ)

  def _update_now(self):
    self.updater_proc.send_signal(signal.SIGHUP)

  def test_no_update(self):
    self.params.put("IsOffroad", "1")
    time.sleep(1)
    self._start_updater()

    time.sleep(1)

    # let the updater run for 5 cycles without an update
    for _ in range(5):
      self._update_now()

      start_time = time.monotonic()
      while self.params.get("LastUpdateTime") is None:
        if time.monotonic() - start_time > 30:
          raise Exception("failed to complete cycle in 30s")
        time.sleep(0.05)

      # TODO: check the last update time is recent
      #self.params.get("LastUpdateTime")
      self.assertTrue(self.params.get("UpdateAvailable") != b"1")
      self.params.delete("LastUpdateTime")

  def test_update(self):
    self.params.put("IsOffroad", "1")
    self._start_updater()

    # make some fake commits in our remote
    self._run([
      "git config user.email tester@testing.com",
      "git config user.name Testy Tester",
      "git commit --allow-empty -m 'an update'",
    ], cwd=self.git_remote_dir)

    self._update_now()
    start_time = time.monotonic()
    while self.params.get("LastUpdateTime") is None:
      if time.monotonic() - start_time > 60:
        raise Exception("failed to complete cycle in 60s")
      time.sleep(0.05)
    self.assertEqual(self.params.get("UpdateAvailable"), b"1")


  #def test_update_now(self):
  #  pass

  #def test_release_notes(self):
  #  pass

  #def test_disable_updates_param(self):
  #  pass

if __name__ == "__main__":
  unittest.main()
