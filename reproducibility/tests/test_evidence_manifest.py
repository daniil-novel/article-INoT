import pytest
from reproducibility.evidence_manifest import write,verify


def test_exact_byte_and_complete_file_set_verification(tmp_path):
    file=tmp_path/'raw.txt';file.write_bytes(b'prompt\r\nanswer\n')
    write(tmp_path)
    assert verify(tmp_path)['files']==1
    file.write_bytes(b'prompt\nanswer\n')
    with pytest.raises(ValueError):verify(tmp_path)
    file.write_bytes(b'prompt\r\nanswer\n')
    (tmp_path/'unexpected.txt').write_text('extra')
    with pytest.raises(ValueError):verify(tmp_path)
