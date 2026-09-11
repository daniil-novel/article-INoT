"""Source-only task overlap audit; never opens generation or outcome records."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import io
import itertools
import json
import keyword
from pathlib import Path
import re
import tokenize

ROOT = Path(__file__).resolve().parents[2]
STARTER = "You should write self-contained code starting with:"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def prompt_features(text: str) -> tuple[str, set[tuple[str, ...]]]:
    exact = " ".join(text.split())
    words = re.findall(r"\w+", text.split(STARTER, 1)[0].casefold())
    return exact, {tuple(words[i:i + 5]) for i in range(len(words) - 4)}


def code_features(code: str) -> dict:
    tree = ast.parse(code)
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                value = node.body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    doc = node.body[0]
                    spans.append(((doc.lineno, doc.col_offset), (doc.end_lineno, doc.end_col_offset)))
                    node.body = node.body[1:]
    tokens = []; identifiers = 0
    for tok in tokenize.generate_tokens(io.StringIO(code).readline):
        if any(start <= tok.start < end for start, end in spans):
            continue
        if tok.type == tokenize.NAME and not keyword.iskeyword(tok.string):
            tokens.append(tok.string); identifiers += 1
        elif tok.type in (tokenize.STRING, tokenize.NUMBER):
            tokens.append(tok.string)
    return {"ast_sha256": digest(ast.dump(tree, include_attributes=False).encode()),
            "tokens": Counter(tokens), "identifiers": identifiers}


def jaccard(a: set, b: set) -> tuple[int, int]:
    intersection = len(a & b)
    return intersection, len(a) + len(b) - intersection


def components(ids: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    parent = {task: task for task in ids}
    def find(task):
        while parent[task] != task:
            parent[task] = parent[parent[task]]; task = parent[task]
        return task
    for left, right in edges:
        a, b = find(left), find(right)
        if a != b: parent[max(a, b)] = min(a, b)
    grouped = defaultdict(list)
    for task in sorted(ids): grouped[find(task)].append(task)
    return sorted(grouped.values(), key=lambda group: group[0])


def exact_groups(values: dict[str, str]) -> list[list[str]]:
    groups = defaultdict(list)
    for task, value in values.items(): groups[value].append(task)
    return sorted([sorted(group) for group in groups.values() if len(group) > 1])


def source_inputs(source: Path, inputs: Path) -> tuple[dict, dict, dict]:
    selection = json.loads((inputs / "selection.json").read_text(encoding="utf-8"))
    if digest(source.read_bytes()) != selection["source_dataset_sha256"]:
        raise ValueError("Source dataset differs from the frozen allocation")
    rows = {}; raw_hashes = {}
    for line in source.read_bytes().splitlines():
        if not line.strip(): continue
        row = json.loads(line); task = row["task_id"]
        if task in rows: raise ValueError("Duplicate source task ID")
        rows[task] = row; raw_hashes[task] = digest(line)
    assigned = selection["assigned_task_ids"]
    if len(rows) != 1140 or len(assigned) != 1000 or len(set(assigned)) != 1000:
        raise ValueError("Source or allocation cardinality changed")
    if any(raw_hashes.get(task) != selection["source_row_sha256"][task] for task in assigned):
        raise ValueError("Selected source row bytes changed")
    prepared = inputs / "input/prepared.jsonl"
    if digest(prepared.read_bytes()) != selection["model_input_sha256"]:
        raise ValueError("Frozen model inputs changed")
    model = [json.loads(line) for line in prepared.read_text(encoding="utf-8").splitlines() if line.strip()]
    if [r["task_id"] for r in model] != assigned:
        raise ValueError("Model input order or identities changed")
    for row in model:
        task = rows[row["task_id"]]
        if row["prompt"] != task["instruct_prompt"] or row["context"] != task["code_prompt"]:
            raise ValueError("Model input differs from source task")
    old, new = set(selection["prior_primary_task_ids"]), set(selection["new_task_ids"])
    if len(old) != 200 or len(new) != 800 or old & new or old | new != set(assigned):
        raise ValueError("The 200/800 partition changed")
    extension_path = ROOT / "reproducibility/segregation80/inputs-v2/selection.json"
    split_path = ROOT / "reproducibility/data/bigcodebench-split/prepare_manifest.json"
    if digest(extension_path.read_bytes()) != selection["extension_selection_sha256"] or digest(split_path.read_bytes()) != selection["source_split_sha256"]:
        raise ValueError("Source subset definitions changed")
    extension = json.loads(extension_path.read_text()); split = json.loads(split_path.read_text())
    subsets = {"old200": old, "new800": new, "development": set(split["dev_task_ids"]),
        "segregation80": set(extension["assigned_task_ids"]), "examples": {f"BigCodeBench/{i}" for i in range(8)}}
    subsets["other_reserved"] = set(rows) - set().union(*subsets.values())
    return selection, rows, subsets


def run(source: Path, inputs: Path, output: Path) -> dict:
    if output.exists(): raise FileExistsError("Refusing to overwrite an audit")
    selection, rows, subsets = source_inputs(source, inputs)
    ids = sorted(rows); assigned = set(selection["assigned_task_ids"])
    prompts = {}; shingles = {}; code = {}; failures = []; fingerprints = []
    for task in ids:
        row = rows[task]; prompts[task], shingles[task] = prompt_features(row["instruct_prompt"])
        try: code[task] = code_features(row["code_prompt"] + row["canonical_solution"])
        except (SyntaxError, tokenize.TokenError, IndentationError) as exc:
            failures.append({"task_id": task, "error_type": type(exc).__name__, "message": str(exc)})
        fingerprints.append({"task_id": task, "assigned": task in assigned,
            "instruction_sha256": digest(prompts[task].encode()), "prompt_shingles": len(shingles[task]),
            "reference_ast_sha256": code.get(task, {}).get("ast_sha256"),
            "reference_identifiers": code.get(task, {}).get("identifiers")})
    graphs = {name: [] for name in ("prompt_050", "prompt_070", "prompt_090", "near_code", "exact_instruction", "exact_ast")}
    edges = []
    exact = {"exact_instruction": exact_groups(prompts),
             "exact_ast": exact_groups({task: value["ast_sha256"] for task, value in code.items()})}
    for name, groups in exact.items():
        for group in groups:
            graphs[name].extend(itertools.combinations(group, 2))
    code_sets = {task: set(value["tokens"]) for task, value in code.items()}
    for left, right in itertools.combinations(ids, 2):
        pi, pu = jaccard(shingles[left], shingles[right])
        qualifies = []
        if shingles[left] and shingles[right]:
            for threshold in (50, 70, 90):
                if 100 * pi >= threshold * pu:
                    name = f"prompt_{threshold:03d}"; graphs[name].append((left, right)); qualifies.append(name)
        ci = cu = mi = mu = None
        if left in code and right in code and min(code[left]["identifiers"], code[right]["identifiers"]) >= 20:
            ci, cu = jaccard(code_sets[left], code_sets[right])
            if cu and 100 * ci >= 80 * cu:
                a, b = code[left]["tokens"], code[right]["tokens"]
                mi = sum((a & b).values()); mu = sum((a | b).values())
                if 100 * mi >= 70 * mu:
                    graphs["near_code"].append((left, right)); qualifies.append("near_code")
        if qualifies:
            edges.append({"left": left, "right": right, "graphs": qualifies,
                "prompt_jaccard": pi / pu if pu else None,
                "code_set_jaccard": ci / cu if cu else None,
                "code_multiset_jaccard": mi / mu if mu else None})
    graphs["union_070_code_exact"] = sorted(set().union(*(set(graphs[name]) for name in
        ("prompt_070", "near_code", "exact_instruction", "exact_ast"))))
    partitions = {}; graph_summary = {}
    for name, links in graphs.items():
        full = components(ids, links)
        projected = [sorted(set(group) & assigned) for group in full if set(group) & assigned]
        sizes = [len(group) for group in projected]
        cross = {}
        for label, subset in subsets.items():
            cross[label] = {"components": sum(bool(set(g) & assigned) and bool(set(g) & subset) and
                 bool(set(g) & (assigned - subset)) for g in full),
                 "assigned_tasks_linked_to_other_subset": sorted(set().union(*(set(g) & (assigned - subset)
                    for g in full if set(g) & subset)))}
        partitions[name] = {"source_components": full, "assigned_components": projected}
        graph_summary[name] = {"edges": len(links), "source_components": len(full),
            "assigned_components": len(projected), "assigned_non_singleton_components": sum(n > 1 for n in sizes),
            "assigned_tasks_in_non_singletons": sum(n for n in sizes if n > 1), "largest_assigned_component": max(sizes),
            "component_size_histogram": dict(sorted(Counter(sizes).items())), "cross_subset": cross}
    report = {"schema": "source-task-overlap-v1", "source_count": len(rows), "assigned_count": len(assigned),
        "source_sha256": digest(source.read_bytes()), "selection_sha256": digest((inputs / "selection.json").read_bytes()),
        "protocol_sha256": digest((Path(__file__).parent / "PROTOCOL.md").read_bytes()),
        "script_sha256": digest(Path(__file__).read_bytes()), "model_outcomes_read": False,
        "exact_groups": exact, "graphs": graph_summary, "reference_parse_errors": failures,
        "short_instructions": [task for task in ids if not shingles[task]],
        "short_reference_programs": [task for task in ids if task in code and code[task]["identifiers"] < 20],
        "limitations": ["Lexical/AST similarity is not semantic equivalence or proof of error dependence.",
          "Singleton tasks may remain correlated; training contamination is not identifiable from these files.",
          "No task is removed and no frozen confirmatory rule is changed."]}
    output.mkdir(parents=True)
    for name, data in (("summary.json", report), ("partitions.json", partitions)):
        (output / name).write_bytes(encoded(data))
    for name, data in (("edges.jsonl", edges), ("fingerprints.jsonl", fingerprints)):
        (output / name).write_bytes(b"".join(encoded(row) for row in data))
    return {"source_count": len(rows), "assigned_count": len(assigned), "parse_errors": len(failures),
            "graphs": {name: {k: value[k] for k in ("edges", "assigned_components", "largest_assigned_component")}
                       for name, value in graph_summary.items()}}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source", type=Path, default=ROOT / "reproducibility/data/bigcodebench-v0.1.4.jsonl")
    p.add_argument("--inputs", type=Path, default=ROOT / "reproducibility/scale1000/inputs-v1")
    a = p.parse_args(); print(json.dumps(run(a.source, a.inputs, a.output)))
