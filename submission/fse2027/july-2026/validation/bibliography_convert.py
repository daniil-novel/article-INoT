"""Convert the selected July manuscript bibliography without changing its sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SOURCE_COMMIT = "173a16c30488208db26acd51c20e2243430e54e0"
SOURCE_FILE = "converted_article_springer.tex"
SOURCE_SHA256 = "536b63ff989c0009dd0f1eb7bd4de663ec86c8c661f18afdb775104fed77f3d8"
ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "paper" / "references.bib"
UNCITED = ["austin2021mbpp", "goncalves2011", "ko2007", "parnin2011"]

# Initials, source "et al." elisions, venue abbreviations, dates, and identifiers
# are preserved. This conversion does not add unverified reference metadata.
RECORDS = [
    ("misc", "sun2025inot", {
        "author": "Sun, H. and Zeng, S.",
        "title": "Introspection of Thought Helps AI Agents",
        "howpublished": "arXiv preprint",
        "note": "arXiv:2507.08664",
        "year": "2025",
    }),
    ("inproceedings", "ko2007", {
        "author": "Ko, A. J. and DeLine, R. and Venolia, G.",
        "title": "Information Needs in Collocated Software Development Teams",
        "booktitle": r"Proc.\ 29th Int.\ Conf.\ Software Engineering",
        "year": "2007",
        "pages": "344--353",
    }),
    ("article", "parnin2011", {
        "author": "Parnin, C. and Rugaber, S.",
        "title": "Resumption Strategies for Interrupted Programming Tasks",
        "journal": "Software Quality Journal",
        "volume": "19",
        "number": "1",
        "pages": "5--34",
        "year": "2011",
    }),
    ("article", "goncalves2011", {
        "author": "Goncalves, M. K. and de Souza, C. R. B. and Gonzalez, V. M.",
        "title": "Collaboration, Information Seeking and Communication",
        "journal": r"J.\ Universal Computer Science",
        "volume": "17",
        "number": "11",
        "pages": "1529--1550",
        "year": "2011",
    }),
    ("inproceedings", "wei2022cot", {
        "author": "Wei, J. and others",
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "booktitle": "NeurIPS",
        "volume": "35",
        "year": "2022",
        "pages": "24824--24837",
    }),
    ("inproceedings", "yao2022react", {
        "author": "Yao, S. and others",
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "booktitle": "ICLR",
        "year": "2023",
    }),
    ("inproceedings", "madaan2023selfrefine", {
        "author": "Madaan, A. and others",
        "title": "Self-Refine: Iterative Refinement with Self-Feedback",
        "booktitle": "NeurIPS",
        "year": "2023",
    }),
    ("inproceedings", "shinn2023reflexion", {
        "author": "Shinn, N. and others",
        "title": "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "booktitle": "NeurIPS",
        "year": "2023",
    }),
    ("inproceedings", "turpin2023unfaithful", {
        "author": "Turpin, M. and Michael, J. and Perez, E. and Bowman, S. R.",
        "title": "Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting",
        "booktitle": "NeurIPS",
        "year": "2023",
    }),
    ("book", "weiss1999", {
        "author": "Weiss, G.",
        "title": "Multiagent Systems",
        "publisher": "MIT Press",
        "year": "1999",
    }),
    ("book", "wooldridge2009", {
        "author": "Wooldridge, M.",
        "title": "An Introduction to MultiAgent Systems",
        "edition": "2",
        "publisher": "Wiley",
        "year": "2009",
    }),
    ("inproceedings", "hong2023metagpt", {
        "author": "Hong, S. and others",
        "title": "MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework",
        "booktitle": "ICLR",
        "year": "2024",
    }),
    ("inproceedings", "qian2023chatdev", {
        "author": "Qian, C. and others",
        "title": "ChatDev: Communicative Agents for Software Development",
        "booktitle": "ACL",
        "year": "2024",
    }),
    ("misc", "guo2024survey", {
        "author": "Guo, T. and others",
        "title": "Large Language Model based Multi-Agents: A Survey of Progress and Challenges",
        "note": "arXiv:2402.01680",
        "year": "2024",
    }),
    ("misc", "qian2024scaling", {
        "author": "Qian, C. and others",
        "title": "Scaling Large Language Model-based Multi-Agent Collaboration",
        "note": "arXiv:2406.07155",
        "year": "2024",
    }),
    ("inproceedings", "jimenez2023swebench", {
        "author": "Jimenez, C. E. and others",
        "title": "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?",
        "booktitle": "ICLR",
        "year": "2024",
    }),
    ("inproceedings", "yang2024sweagent", {
        "author": "Yang, J. and others",
        "title": "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering",
        "booktitle": "NeurIPS",
        "year": "2024",
    }),
    ("misc", "chen2021humaneval", {
        "author": "Chen, M. and others",
        "title": "Evaluating Large Language Models Trained on Code",
        "note": "arXiv:2107.03374",
        "year": "2021",
    }),
    ("misc", "austin2021mbpp", {
        "author": "Austin, J. and others",
        "title": "Program Synthesis with Large Language Models",
        "note": "arXiv:2108.07732",
        "year": "2021",
    }),
    ("inproceedings", "jiang2023longllmlingua", {
        "author": "Jiang, H. and others",
        "title": "LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression",
        "booktitle": "ACL",
        "year": "2024",
    }),
    ("inproceedings", "pan2024llmlingua2", {
        "author": "Pan, Z. and others",
        "title": "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression",
        "booktitle": "ACL Findings",
        "year": "2024",
    }),
    ("misc", "jia2026compression", {
        "author": "Jia, H. and Barr, E. T. and Mechtaev, S.",
        "title": "Compressing Code Context for LLM-based Issue Resolution",
        "note": "arXiv:2603.28119",
        "year": "2026",
    }),
    ("misc", "bi2024cocogen", {
        "author": "Bi, Z. and others",
        "title": "Iterative Refinement of Project-Level Code Context for Precise Code Generation with Compiler Feedback",
        "note": "arXiv:2403.16792",
        "year": "2024",
    }),
    ("misc", "su2025static", {
        "author": "Su, C.-Y. and McMillan, C.",
        "title": "Do Code LLMs Do Static Analysis?",
        "note": "arXiv:2505.12118",
        "year": "2025",
    }),
    ("misc", "sepidband2025complexity", {
        "author": "Sepidband, M. and Taherkhani, H. and Wang, S. and Hemmati, H.",
        "title": "Enhancing LLM-Based Code Generation with Complexity Metrics",
        "note": "arXiv:2505.23953",
        "year": "2025",
    }),
    ("techreport", "iso25010", {
        "author": "{ISO/IEC}",
        "title": "Systems and software engineering~--- SQuaRE~--- Product quality model",
        "type": "Standard",
        "number": "ISO/IEC 25010:2023",
        "institution": "ISO",
        "year": "2023",
    }),
    ("article", "mccabe1976", {
        "author": "McCabe, T. J.",
        "title": "A Complexity Measure",
        "journal": r"IEEE Trans.\ Software Engineering",
        "volume": "SE-2",
        "number": "4",
        "pages": "308--320",
        "year": "1976",
    }),
    ("misc", "inotresearch2026", {
        "author": "{Anonymous authors}",
        "title": "Hybrid-INoT replication package",
        "year": "2026",
        "note": "Anonymous review artifact supplied with this manuscript",
    }),
    ("misc", "openrouterpro2026", {
        "author": "{OpenRouter}",
        "title": "Gemini 3.1 Pro Preview~--- pricing",
        "year": "2026",
        "url": "https://openrouter.ai/google/gemini-3.1-pro-preview/pricing",
        "note": "Accessed: 26 July 2026",
    }),
    ("misc", "openrouterflash2026", {
        "author": "{OpenRouter}",
        "title": "Gemini 3.1 Flash Lite Preview~--- pricing",
        "year": "2026",
        "url": "https://openrouter.ai/google/gemini-3.1-flash-lite/pricing",
        "note": "Accessed: 26 July 2026",
    }),
]


def render() -> str:
    lines = [
        "% Bibliographic content preserved from the selected July manuscript.",
        "% Initials and source et-al abbreviations are retained without enrichment.",
        "% The replication-package reference is anonymized for review.",
        "",
    ]
    for entry_type, key, fields in RECORDS:
        lines.append(f"@{entry_type}{{{key},")
        for name, value in fields.items():
            # Protect exact title capitalization, including model and method names.
            if name == "title":
                value = "{" + value + "}"
            lines.append(f"  {name} = {{{value}}},")
        lines.extend(["}", ""])
    return "\n".join(lines)


def validate(source: bytes, bibliography: str) -> dict:
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256
    manuscript = source.decode("utf-8")
    source_keys = re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", manuscript)
    output_keys = re.findall(r"^@\w+\{([^,]+),", bibliography, flags=re.MULTILINE)
    cite_groups = re.findall(r"\\(?:cite|citep|citet)\*?(?:\[[^\]]*\])?\{([^}]+)\}", manuscript)
    cited_keys = {key.strip() for group in cite_groups for key in group.split(",")}
    assert source_keys == output_keys
    assert len(output_keys) == len(set(output_keys)) == 30
    assert sorted(set(source_keys) - cited_keys) == UNCITED
    assert not cited_keys - set(output_keys)
    source_entries = {
        match.group(1): match.group(2).strip()
        for match in re.finditer(
            r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\})",
            manuscript,
            flags=re.DOTALL,
        )
    }

    def normalize(value: str) -> str:
        value = value.replace(r"\emph", "")
        value = re.sub(r"\b(?:and|in)\b", "", value)
        return re.sub(r"[\s{},~\\]", "", value)

    metadata_checks = []
    for _, key, fields in RECORDS:
        if key == "inotresearch2026":
            metadata_checks.append({"key": key, "status": "anonymous_exception"})
            continue
        original = source_entries[key]
        quoted_title = re.search(chr(96) * 2 + r"(.*?)''", original, flags=re.DOTALL)
        book_title = re.search(r"\\emph\{([^}]+)\}", original)
        title_match = quoted_title or book_title
        assert title_match is not None, key
        assert normalize(title_match.group(1)) == normalize(fields["title"]), key
        assert re.search(rf"(?<!\d){fields['year']}(?!\d)", original), key
        if key != "iso25010":
            source_author = original[:title_match.start()]
            names = []
            for name in fields["author"].split(" and "):
                if name == "others":
                    names.append("et al.")
                elif "," in name:
                    last, first = name.split(",", 1)
                    names.append(first.strip() + " " + last.strip())
                else:
                    names.append(name)
            assert normalize(source_author) == normalize(" and ".join(names)), key
        for name, value in fields.items():
            if name in {"author", "title", "year", "type"}:
                continue
            if name == "edition":
                assert f"{value}nd" in original, key
            elif name == "note" and value.startswith("Accessed: "):
                assert normalize(value) in normalize(original), key
            else:
                assert normalize(value) in normalize(original), (key, name)
        metadata_checks.append({"key": key, "status": "source_metadata_preserved"})
    anonymous = next(fields for _, key, fields in RECORDS if key == "inotresearch2026")
    assert anonymous == {
        "author": "{Anonymous authors}",
        "title": "Hybrid-INoT replication package",
        "year": "2026",
        "note": "Anonymous review artifact supplied with this manuscript",
    }
    # Existing third-party pricing URLs remain source bibliography metadata.
    assert "url" not in anonymous
    assert set(re.findall(r"https?://[^\s}]+", bibliography)) == {
        "https://openrouter.ai/google/gemini-3.1-pro-preview/pricing",
        "https://openrouter.ai/google/gemini-3.1-flash-lite/pricing",
    }
    return {
        "status": "PASS",
        "source_commit": SOURCE_COMMIT,
        "source_file": SOURCE_FILE,
        "source_sha256": SOURCE_SHA256,
        "bibtex_sha256": hashlib.sha256(bibliography.encode("utf-8")).hexdigest(),
        "source_bibitem_count": len(source_keys),
        "output_entry_count": len(output_keys),
        "citation_occurrences": len(cite_groups),
        "unique_cited_keys": len(cited_keys),
        "source_key_order_preserved": source_keys == output_keys,
        "missing_cited_keys": sorted(cited_keys - set(output_keys)),
        "uncited_keys_requiring_nocite": UNCITED,
        "citation_configuration": [
            r"\citestyle{acmnumeric}",
            r"\bibliographystyle{ACM-Reference-Format}",
            r"\nocite{austin2021mbpp,goncalves2011,ko2007,parnin2011}",
            r"\bibliography{references}",
        ],
        "anonymized_reference_key": "inotresearch2026",
        "anonymized_reference_fields": anonymous,
        "metadata_policy": (
            "Preserve original initials, author-list elisions, titles, venue "
            "abbreviations, years, pages, volumes, issues, arXiv identifiers, "
            "pricing URLs and access dates; do not enrich unverified metadata."
        ),
        "science_text_changed": False,
        "reference_metadata_reaudited": False,
        "metadata_parity_checks": metadata_checks,
        "entries": [
            {
                "key": key,
                "type": entry_type,
                "fields": fields,
                "change": "anonymization" if key == "inotresearch2026" else "format_conversion",
            }
            for entry_type, key, fields in RECORDS
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate existing output without writing.")
    args = parser.parse_args()
    source = subprocess.check_output(
        ["git", "show", f"{SOURCE_COMMIT}:{SOURCE_FILE}"], cwd=ROOT
    )
    expected = render()
    report = validate(source, expected)
    if args.check:
        assert DESTINATION.read_text(encoding="utf-8") == expected
    else:
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        DESTINATION.write_text(expected, encoding="utf-8", newline="\n")
        (ROOT / "validation" / "bibliography_conversion.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({
        "status": report["status"],
        "entry_count": report["output_entry_count"],
        "cited_key_count": report["unique_cited_keys"],
        "uncited_keys": report["uncited_keys_requiring_nocite"],
        "bibtex_sha256": report["bibtex_sha256"],
    }))


if __name__ == "__main__":
    main()
