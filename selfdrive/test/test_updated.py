#!/usr/bin/env python3
import os
import unittest
import tempfile
import subprocess

from common.basedir import BASEDIR
from common.params import Params


class TestUpdater(unittest.TestCase):

  def setUp(self):
    self.params = Params()
    self.params.clear_all()

    self.basedir = tempfile.mkdtemp()
    self.git_remote_dir = tempfile.mkdtemp()
    self.staging_dir = tempfile.mkdtemp()
    os.environ["UPDATER_STAGING_ROOT"] = self.staging_dir

    # setup two git repos
    self._run([
      f"git clone {BASEDIR} {self.git_remote_dir}",
      f"git clone {self.git_remote_dir} {self.basedir}",
    ])

    # start updater
    updated_path = os.path.join(self.basedir, "selfdrive/updated.py")
    self.updater_proc = subprocess.Popen(updated_path, env={
      "PYTHONPATH": self.staging_dir,
      "UPDATER_TESTING": "1",
      "UPDATER_STAGING_ROOT": self.staging_dir,
    })

  def tearDown(self):
    self.updater_proc.terminate()
    self.updater_proc.wait(10)

  def _run(self, cmd, cwd=None):
    if not isinstance(cmd, list):
      cmd = (cmd,)

    for c in cmd:
      subprocess.check_output(c, cwd=cwd, shell=True)

  def test_update(self):
    # make some fake commits in our remote
    self._run([
      "git config user.email tester@testing.com",
      "git config user.name Testy Tester",
      "git commit --allow-empty -m 'an update'",
    ], cwd=self.git_remote_dir)

    # start updater

  #def test_update_now(self):
  #  pass

  #def test_release_notes(self):
  #  pass

if __name__ == "__main__":
  unittest.main()
