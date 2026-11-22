"""Read local YAML rules and translate them to Rime dictionary entries."""
import fcntl
import os
import re
import tempfile
from pathlib import Path

from ruamel.yaml import YAML


def codec():
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.allow_unicode = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def personal_rows(path):
    if not path.exists():
        return []
    entries = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" in line:
            fields = line.split("\t")
        else:
            # Only ASCII spaces separate fields. A full-width space can be a word.
            fields = [value for value in line.split(" ") if value]
        try:
            if len(fields) not in (2, 3) or not all(fields[:2]):
                raise ValueError
            if len(fields) == 3:
                int(fields[2])
        except ValueError:
            raise ValueError(f"{path}:{number}: expected word code [integer weight]; "
                             "use tabs for words containing spaces") from None
        entries.append("\t".join(fields))
    return entries


def load_rules(directory):
    path = directory / "personal.yaml"
    if path.exists():
        with path.open() as stream:
            data = codec().load(stream)
        return {} if data is None else data

    rules = {"words": [], "top": [], "delete": []}
    for section in rules:
        base = directory / section
        for suffix in (".tsv", ".txt"):
            for line in personal_rows(base.with_suffix(suffix)):
                word, code, *weight = line.split("\t")
                item = {"code": code}
                dest = section
                stem, separator, comment = word.rpartition("`")
                if separator and stem and comment and section != "delete":
                    if comment == "[删]" and section == "words":
                        dest = "delete"
                        item["text"] = stem
                    elif stem.startswith("$") and re.fullmatch(r"[A-Za-z0-9]+", stem[1:]):
                        item.update(target=stem[1:], label=comment)
                    else:
                        item.update(text=stem, comment=comment)
                else:
                    item["text"] = word
                if weight:
                    item["weight"] = int(weight[0])
                rules[dest].append(item)
    return rules


def compile_entry(entry, section):
    if not isinstance(entry, dict):
        raise ValueError("expected a mapping")
    jump = "target" in entry
    required = {"code", "target", "label"} if jump else {"code", "text"}
    allowed = required | {"weight"}
    if not jump and section != "delete":
        allowed.add("comment")
    if not required <= entry.keys() <= allowed or (jump and section == "delete"):
        raise ValueError("invalid or missing fields")
    for key in entry.keys() - {"weight"}:
        value = entry[key]
        if not isinstance(value, str) or not value or any(c in value for c in "\t\r\n"):
            raise ValueError(f"{key} must be a nonempty, single-line string")
    if jump:
        if not re.fullmatch(r"[A-Za-z0-9]+", entry["target"]) or "`" in entry["label"]:
            raise ValueError("expected an alphanumeric target and a label without backticks")
        word = "$" + entry["target"] + "`" + entry["label"]
    else:
        word = entry["text"]
        if section == "delete":
            word += "`[删]"
        elif "comment" in entry:
            if "`" in entry["comment"]:
                raise ValueError("comment cannot contain a backtick")
            word += "`" + entry["comment"]
    fields = [word, entry["code"]]
    if "weight" in entry:
        if not isinstance(entry["weight"], int) or isinstance(entry["weight"], bool):
            raise ValueError("weight must be an integer")
        fields.append(str(entry["weight"]))
    return "\t".join(fields)


def table_rows(rules):
    if not isinstance(rules, dict) or set(rules) - {"words", "top", "delete"}:
        raise ValueError("personal.yaml expects words, top or delete sections")
    tables = {"personal": [], "personal.top": []}
    for section in ("words", "top", "delete"):
        entries = rules.get(section, [])
        if not isinstance(entries, list):
            raise ValueError(f"{section} must be a list")
        table = tables["personal.top" if section == "top" else "personal"]
        for index, entry in enumerate(entries, 1):
            try:
                table.append(compile_entry(entry, section))
            except ValueError as error:
                raise ValueError(f"personal.yaml: {section} entry {index}: {error}") from error
    return tables


def save_rules(directory, section=None, entry=None):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "personal.yaml"
    with (directory / ".personal.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rules = load_rules(directory)
        table_rows(rules)
        if section is not None:
            compile_entry(entry, section)
            rules.setdefault(section, []).append(entry)
        elif path.exists():
            return path
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as stream:
            tmp = Path(stream.name)
            try:
                codec().dump(rules, stream)
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)
    return path
