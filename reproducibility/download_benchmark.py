"""Download the pinned official BigCodeBench release; no model requests or evaluation."""
import hashlib
import json
from pathlib import Path
import urllib.request

REVISION = 'b74c0d0bf70d2c0bc459be537895cca163007f1a'
SHA256 = 'd9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267'
URL = f'https://huggingface.co/datasets/bigcode/bigcodebench/resolve/{REVISION}/data/v0.1.4-00000-of-00001.parquet'


def main():
    import pyarrow.parquet as pq
    root=Path(__file__).resolve().parent
    data=root/'data';data.mkdir(exist_ok=True)
    parquet=data/'bigcodebench-v0.1.4.parquet'
    if not parquet.exists():urllib.request.urlretrieve(URL,parquet)
    if hashlib.sha256(parquet.read_bytes()).hexdigest()!=SHA256:
        raise ValueError('Official dataset checksum mismatch')
    rows=pq.read_table(parquet).to_pylist()
    if len(rows)!=1140 or len({r['task_id'] for r in rows})!=1140:raise ValueError('Unexpected dataset size')
    output=data/'bigcodebench-v0.1.4.jsonl'
    output.write_bytes(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows).encode('utf-8'))
    record={'source_url':URL,'dataset_revision':REVISION,'release':'v0.1.4','rows':len(rows),'fields':list(rows[0]),
            'parquet_sha256':SHA256,'jsonl_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'serialization':'UTF-8 JSONL, LF'}
    (root/'revision'/'dataset_source.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'parquet_sha256':SHA256,'output':str(output)}))


if __name__=='__main__':main()
