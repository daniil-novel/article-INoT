import copy
import pytest
from reproducibility.scc2000.resume_snapshot import extend_inventory
from reproducibility.scc2000.continuation import canonical_digest


def fixture():
    rows=[{"id":"old","files_sha256":{"status.json":"historical"}}]
    return {"selected_ids":["old","new","untouched"],"selected_cells_digest":"fixed",
            "old_inventory":{"assignments":rows,"snapshot_sha256":canonical_digest(rows),"assignment_count":1}}


def test_preserves_original_recovery_hashes_and_scientific_selection():
    old=fixture();before=copy.deepcopy(old)
    current={"assignments":[{"id":"old","files_sha256":{"status.json":"recovered"}},
                             {"id":"new","files_sha256":{"status.json":"terminal"}}]}
    out=extend_inventory(old,current)
    assert old==before and out["selected_ids"]==old["selected_ids"]
    assert out["selected_cells_digest"]=="fixed"
    assert next(x for x in out["old_inventory"]["assignments"] if x["id"]=="old")["files_sha256"]["status.json"]=="historical"
    assert out["old_inventory"]["assignment_count"]==2


@pytest.mark.parametrize("ids",[["new"],["old","other"],["old","old"]])
def test_rejects_missing_unselected_and_duplicate_ids(ids):
    with pytest.raises(ValueError): extend_inventory(fixture(),{"assignments":[{"id":i} for i in ids]})
