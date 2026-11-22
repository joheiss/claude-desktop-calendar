"""Setzt eine vdirsyncer-Konfiguration aus Bausteinen zusammen."""
import os
import pathlib

CONFIG_DIR = pathlib.Path(__file__).resolve().parent.parent / "config"
REAL_VALUES = pathlib.Path.home() / ".config/vdirsyncer/real-values.env"
REAL_STATUS = pathlib.Path.home() / ".config/vdirsyncer/status"
CA_BUNDLE = pathlib.Path.home() / ".config/vdirsyncer/ca-bundle.pem"


def _read_env(path: pathlib.Path) -> dict:
    values = {}
    for line in path.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def build_config(mode: str, storages: str, out: pathlib.Path) -> pathlib.Path:
    if mode not in ("import", "mirror", "gcopy"):
        raise ValueError(f"unknown mode: {mode}")
    read_only = "read_only = true" if mode in ("mirror", "gcopy") else ""
    if storages.startswith("test:"):
        base = pathlib.Path(storages[len("test:"):])
        template = "storages-test.cfg.tpl"
        values = {"A_PATH": str(base / "a"), "B_PATH": str(base / "b"),
                  "STATUS": str(base / "status"), "COLLECTIONS": "null"}
    elif storages == "real":
        template = "storages-real.cfg.tpl"
        env = _read_env(pathlib.Path(os.environ.get("VDIRSYNCER_REAL_VALUES", REAL_VALUES)))
        values = dict(env)
        values["STATUS"] = str(REAL_STATUS)
        values["CA_BUNDLE"] = str(CA_BUNDLE)
        values["COLLECTIONS"] = (
            f'[["main", "{env["GOOGLE_CAL_ID"]}", "{env["STRATO_CAL_NAME"]}"]]'
        )
    else:
        raise ValueError(f"unknown storages: {storages}")
    if mode == "gcopy":
        state = pathlib.Path.home() / ".local/state/calendar-mirror"
        values["STATUS"] = str(state / "status-gcopy")
        values["GCOPY_PATH"] = str(state / "google")
        values["COLLECTIONS"] = f'[["main", "{values["GOOGLE_CAL_ID"]}", "main"]]'
    values["A_READ_ONLY"] = read_only
    text = "\n".join([
        f'[general]\nstatus_path = "{values["STATUS"]}"\n',
        (CONFIG_DIR / f"pair-{mode}.cfg").read_text(),
        (CONFIG_DIR / template).read_text(),
    ])
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    out = pathlib.Path(out)
    out.write_text(text)
    return out


if __name__ == "__main__":
    import sys
    build_config(sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]))
