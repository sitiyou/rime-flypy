"""Generate a fcitx5-rime user profile from the checked-in upstream tables."""
import argparse
import fcntl
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

from personal import load_rules, table_rows

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
PROFILE = ROOT / "profile"
CONFIG = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "rime-flypy"
USER_DIR = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "fcitx5/rime"


def write_table(out, name, entries, sort="original"):
    header = f'---\nname: {name}\nversion: "1"\nsort: {sort}\nuse_preset_vocabulary: false\n...\n'
    (out / f"{name}.dict.yaml").write_text(header + "".join(line + "\n" for line in entries))


def generate(out, personal):
    for schema in ("flypy", "flypydz", "flypyok"):
        for suffix in ("schema.yaml", "dict.yaml"):
            name = f"{schema}.{suffix}"
            shutil.copyfile(ROOT / name, out / name)
    shutil.copytree(ROOT / "flypy", out / "flypy", ignore=shutil.ignore_patterns("flypy.user*.yaml"))
    shutil.copytree(ROOT / "lua", out / "lua")
    for src in PROFILE.glob("*.yaml"):
        shutil.copyfile(src, out / src.name)

    dictionary = yaml.safe_load((ROOT / "flypy.dict.yaml").read_text())
    tables = dictionary["import_tables"]
    tables.insert(tables.index("flypy/flypy.secondary"), "flypy/flypy.secondary.short.code")
    tables[:0] = ["flypy.personal.top", "flypy.o-symbols"]
    tables.append("flypy.personal")
    rules = load_rules(personal)
    for suffix, entries in table_rows(rules).items():
        write_table(out, "flypy." + suffix, entries, sort="by_weight")

    # Offer a fourth-key hint only when no active exact-code table owns the prefix.
    symbols = (out / "flypy.o-symbols.dict.yaml").read_text().split("\n...", 1)[1]
    reserved = {line.split("\t")[1] for line in symbols.splitlines() if "\t" in line}
    reserved.add("oc")
    occupied = set()
    hints = {}
    for name in tables:
        path = out / f"{name}.dict.yaml"
        header, source = path.read_text().split("\n...", 1)
        # The original o-prefix shortcuts auto-commit when they have one candidate.
        if name.startswith("flypy/"):
            kept = []
            for line in source.splitlines(keepends=True):
                fields = line.rstrip("\n").split("\t")
                if len(fields) >= 2 and fields[1] in reserved:
                    continue
                kept.append(line)
            source = "".join(kept)
            path.write_text(header + "\n..." + source)
        for line in source.splitlines():
            fields = line.split("\t")
            if line.startswith("#") or len(fields) < 2:
                continue
            word, code = fields[:2]
            occupied.add(code)
            if name == "flypy/flypy.primary" and len(code) == 4 and code.isalpha():
                hints.setdefault(code[:3], (word, code[3]))
    write_table(out, "flypy.hints", [f"{word}`{key}\t{prefix}"
                for prefix, (word, key) in sorted(hints.items()) if prefix not in occupied and not prefix.startswith("o")])
    tables.append("flypy.hints")
    (out / "flypy.dict.yaml").write_text(yaml.safe_dump(dictionary, allow_unicode=True, sort_keys=False))


def compile_profile(out, shared):
    subprocess.run(["rime_deployer", "--build", out, shared, out / "build"], check=True)
    for schema in ("flypy", "flypydz", "flypyok"):
        for suffix in ("schema.yaml", "table.bin", "prism.bin", "reverse.bin"):
            if not (out / "build" / f"{schema}.{suffix}").is_file():
                raise RuntimeError(f"Missing compiled file: {schema}.{suffix}")


def install(out, target):
    if target.is_symlink():
        raise ValueError(f"Replace the old directory symlink before installing into {target}")
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    for src in sorted(out.rglob("*")):
        if not src.is_file() or src.name in {"user.yaml", "installation.yaml"}:
            continue
        dest = target / src.relative_to(out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            shutil.copy2(src, tmp_path)
            tmp_path.chmod(0o600)
            os.replace(tmp_path, dest)
        finally:
            tmp_path.unlink(missing_ok=True)


def digest(out):
    return {p.relative_to(out): hashlib.sha256(p.read_bytes()).digest()
            for p in out.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "verify", "install"))
    parser.add_argument("--personal", type=Path, default=CONFIG)
    parser.add_argument("--target", type=Path, default=USER_DIR)
    parser.add_argument("--shared", type=Path, default=Path("/usr/share/rime-data"))
    args = parser.parse_args()
    BUILD.mkdir(exist_ok=True)
    with (BUILD / ".profile.lock").open("a") as lock, tempfile.TemporaryDirectory(dir=BUILD) as tmp:
        fcntl.flock(lock, fcntl.LOCK_EX)
        out = Path(tmp) / "rime"
        out.mkdir(mode=0o700)
        generate(out, args.personal)
        if args.action == "generate":
            dest = BUILD / "generated"
            if dest.exists():
                shutil.rmtree(dest)
            out.rename(dest)
            print(dest)
        elif args.action == "verify":
            second = Path(tmp) / "second"
            second.mkdir()
            generate(second, args.personal)
            if digest(out) != digest(second):
                raise RuntimeError("Generated files differ between runs")
            compile_profile(out, args.shared)
        else:
            compile_profile(out, args.shared)
            install(out, args.target)


if __name__ == "__main__":
    main()
