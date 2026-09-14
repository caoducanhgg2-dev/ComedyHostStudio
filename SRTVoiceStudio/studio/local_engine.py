"""Lifecycle of an optional, application-owned loopback engine."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
from .audio import check_cancel

class LocalEngine:
    def __init__(self,executable,data,port=10103):
        self.executable=Path(executable);self.data=Path(data);self.port=port
        self.process=None;self.log=None
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def start(self,cancel,progress=lambda _:None):
        check_cancel(cancel)
        if self.process is not None and self.process.poll() is None:return
        self.close()
        with socket.socket() as probe:
            try:probe.bind(('127.0.0.1',self.port))
            except OSError:raise RuntimeError('Cổng engine đang được ứng dụng khác sử dụng.')
        self.data.mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,HF_HUB_OFFLINE='1')
        if os.name!='nt':env['XDG_DATA_HOME']=str(self.data)
        self.log=(self.data/'engine.log').open('ab')
        try:
            self.process=subprocess.Popen([str(self.executable),'--host','127.0.0.1','--port',str(self.port),'--no-use_gpu','--disable_sentry'],
                cwd=self.executable.parent,env=env,stdout=self.log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                check_cancel(cancel)
                if self.process.poll() is not None:raise RuntimeError('Engine không khởi động được. Xem engine.log trong dữ liệu gói.')
                try:
                    with self.opener.open(f'http://127.0.0.1:{self.port}/version',timeout=1) as response:version=json.load(response)
                    if isinstance(version,str):return
                except (OSError,ValueError):pass
                progress('Đang nạp engine offline…');cancel.wait(.25)
            raise RuntimeError('Engine khởi động quá thời gian cho phép.')
        except Exception:self.close();raise
    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            self.process=None
        if self.log is not None:self.log.close();self.log=None
