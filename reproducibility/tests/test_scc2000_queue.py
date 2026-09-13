from pathlib import Path
import pytest
from reproducibility.scc2000.queue_finish import check_process

class Process:
    def __init__(self,module='reproducibility.scc2000.continuation',created=100):self.module=module;self.created=created
    def cmdline(self):return ['python','-m',self.module,'generate']
    def create_time(self):return self.created
    def cwd(self):return str(Path.cwd())

def test_generator_identity_and_pid_reuse():
    check_process(Process(),100,Path.cwd())
    with pytest.raises(ValueError):check_process(Process(created=101),100,Path.cwd())
    with pytest.raises(ValueError):check_process(Process(module='unrelated'),100,Path.cwd())

def test_other_checkout_is_rejected(tmp_path):
    with pytest.raises(ValueError):check_process(Process(),100,tmp_path)
