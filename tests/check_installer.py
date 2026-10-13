"""Exercise SDK selection with a stub SSH that stops before packaging/install."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

source=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'instalar.sh'
subprocess.run(['bash','-n',str(source)],check=True)
with tempfile.TemporaryDirectory(prefix='dva-installer-check-') as temp:
    root=Path(temp)
    here=root/'game'
    here.mkdir()
    shutil.copyfile(source,here/'instalar.sh')
    bundled=here/'r36s_a11y'
    bundled.mkdir()
    sdk=root/'r36s-a11y-sdk'
    cloned=sdk/'python/r36s_a11y'
    cloned.mkdir(parents=True)
    bindir=root/'bin'
    bindir.mkdir()
    ssh=bindir/'ssh'
    ssh.write_text('#!/bin/sh\nexit 0\n')  # says game is active; blocks writes
    ssh.chmod(0o755)
    env=dict(os.environ,PATH=str(bindir)+':'+os.environ['PATH'])
    def selected(*args):
        result=subprocess.run(['bash',str(here/'instalar.sh'),'test-host']+list(args),env=env,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
        assert result.returncode==1,result.stdout
        return result.stdout
    assert str(cloned) in selected()
    explicit=root/'explicit-sdk'
    (explicit/'python/r36s_a11y').mkdir(parents=True)
    assert str(explicit/'python/r36s_a11y') in selected(str(explicit))
    cloned.rmdir()
    assert str(bundled) in selected()
    assert 'SDK não encontrado no caminho solicitado' in selected(str(root/'missing-sdk'))
print('Installer checks passed: clone priority, explicit path, bundled fallback, invalid explicit path')
