"""Isolated browser-test stack; never touches the owner's data or LIVE API."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

root=Path(__file__).resolve().parents[1]
stop_file=Path(os.environ.get('JARVIS_E2E_STOP_FILE',str(root/'data/e2e-stop'))).resolve()
if stop_file.parent != (root/'data').resolve():
    raise RuntimeError('Teststoppfilen måste ligga i projektets data-mapp.')
if os.name=='nt':
    from windows_job import contain_children
    job_handle=contain_children()
sys.path.insert(0,str(root/'backend'))
with tempfile.TemporaryDirectory(prefix='jarvis-e2e-') as folder:
    os.environ.update(JARVIS_DATA_DIR=folder,JARVIS_MODE='DEMO',JARVIS_ORIGIN='http://127.0.0.1:8765',JARVIS_SECURE_COOKIE='false',PYTHONPATH=str(root/'backend'),JARVIS_PAID_ENABLED='false')
    os.environ.pop('OPENAI_API_KEY',None)
    from jarvis.db import initialize
    from jarvis.auth import set_owner
    initialize()
    set_owner('browser-test-only-password')
    processes=[subprocess.Popen([sys.executable,'-m','uvicorn','jarvis.api:app','--host','127.0.0.1','--port','8765'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL),subprocess.Popen([sys.executable,'-m','jarvis.worker'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)]
    try:
        while all(p.poll() is None for p in processes) and not stop_file.exists():time.sleep(0.3)
    finally:
        for p in processes:p.terminate()
        for p in processes:p.wait(timeout=15)
        stop_file.unlink(missing_ok=True)
