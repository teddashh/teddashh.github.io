import importlib.util, json, os, subprocess, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('sync',Path(__file__).with_name('sync_public_source.py')); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SyncTests(unittest.TestCase):
 def test_allowlist(self):
  for p in ['.github/workflows/x.yml','.git/config','CNAME','../README.md','assets/../../x','/README.md']:self.assertFalse(m.allowed(p,'profile'))
  for p in ['README.md','README.zh-TW.md','assets/a.svg','projects/a.md']:self.assertTrue(m.allowed(p,'profile'))
 def test_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x';p.symlink_to('/etc/passwd')
   with self.assertRaises(RuntimeError):m.digest(p)
 def test_public_sync_and_conflict(self):
  import sys
  original=m.git; old=os.getcwd(); argv=sys.argv
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); src=root/'src';dst=root/'dst'
   for p in [src,dst]:p.mkdir();original('init','-q','-b','main',str(p));original('config','user.name','test',cwd=p);original('config','user.email','test@example.com',cwd=p)
   (src/'README.md').write_text('one');original('add','.',cwd=src);original('commit','-qm','initial',cwd=src)
   sha=original('rev-parse','HEAD',cwd=src).decode().strip()
   (dst/'README.md').write_text('one');original('add','.',cwd=dst);original('commit','-qm','initial',cwd=dst)
   def fake(*a,cwd=None):return original(*(str(src) if x=='https://github.com/TED-H-com/teddashh.git' else x for x in a),cwd=cwd)
   m.git=fake;os.chdir(dst);sys.argv=['sync','profile','--initialize',sha];m.main()
   (src/'README.md').write_text('two');(src/'assets').mkdir();(src/'assets/x.svg').write_text('<svg/>');(src/'.github').mkdir();(src/'.github/evil').write_text('ignored');original('add','.',cwd=src);original('commit','-qm','update',cwd=src)
   sys.argv=['sync','profile'];m.main();self.assertEqual((dst/'README.md').read_text(),'two');self.assertFalse((dst/'.github/evil').exists())
   original('add','.',cwd=dst);sys.argv=['sync','profile','--finalize'];m.main();original('add','.',cwd=dst);original('commit','-qm','sync',cwd=dst)
   sys.argv=['sync','profile'];m.main() # unchanged source is a no-op
   (dst/'README.md').write_text('personal edit');(src/'README.md').write_text('three');original('add','.',cwd=src);original('commit','-qm','update again',cwd=src)
   with self.assertRaisesRegex(RuntimeError,'Personal edit detected'):m.main()
  os.chdir(old);m.git=original;sys.argv=argv
class BootstrapAndStageTests(unittest.TestCase):
 def test_bootstrap_stage_deletion_and_manual_noop(self):
  import sys
  original, old, argv = m.git, os.getcwd(), sys.argv
  try:
   with tempfile.TemporaryDirectory() as d:
    root=Path(d); src=root/'src'; dst=root/'dst'
    for p in (src,dst):
     p.mkdir(); original('init','-q','-b','main',str(p)); original('config','user.name','test',cwd=p); original('config','user.email','test@example.com',cwd=p)
     (p/'README.md').write_text('same'); (p/'hub.json').write_text('{}')
     original('add','.',cwd=p); original('commit','-qm','initial',cwd=p)
    sha=original('rev-parse','HEAD',cwd=src).decode().strip()
    def fake(*a,cwd=None):
     return original(*(str(src) if x=='https://github.com/TED-H-com/ted-h-com.github.io.git' else x for x in a),cwd=cwd)
    m.git=fake; os.chdir(dst)
    (dst/'README.md').write_text('mismatch')
    sys.argv=['sync','hub','--initialize',sha]
    with self.assertRaisesRegex(RuntimeError,'do not match'): m.main()
    self.assertFalse(m.STATE.exists())
    (dst/'README.md').write_text('same'); m.main()
    original('add','.'); original('commit','-qm','bootstrap')
    # Manual unchanged-source run still renders, stages and finalizes successfully.
    sys.argv=['sync','hub']; m.main()
    (dst/'site').mkdir(); (dst/'site/index.html').write_text('rendered')
    sys.argv=['sync','hub','--finalize']; m.main()
    self.assertIn('site/index.html', json.loads(m.STATE.read_text())['files'])
    original('commit','-qm','render')
    sys.argv=['sync','hub']; m.main()
    sys.argv=['sync','hub','--finalize']; m.main()
    self.assertEqual(original('diff','--cached','--name-only'),b'')
    # Deleted optional managed file is staged without nonexistent pathspec errors.
    (src/'README.md').unlink(); original('add','-A',cwd=src); original('commit','-qm','remove',cwd=src)
    sys.argv=['sync','hub']; m.main()
    sys.argv=['sync','hub','--finalize']; m.main()
    self.assertIn('D\tREADME.md', original('diff','--cached','--name-status').decode())
    self.assertNotIn('README.md',json.loads(m.STATE.read_text())['files'])
    original('commit','-qm','sync delete')
    (dst/'site/index.html').write_text('personal edit')
    sys.argv=['sync','hub']
    with self.assertRaisesRegex(RuntimeError,'Personal edit detected'): m.main()
  finally:
   os.chdir(old); m.git=original; sys.argv=argv
if __name__=='__main__':unittest.main()
