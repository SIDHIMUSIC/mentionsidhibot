"""Load split handler body."""
from pathlib import Path

_code = (Path(__file__).with_name("ha.py").read_text() + Path(__file__).with_name("hb.py").read_text())
exec(compile(_code, "tools/handlers_full.py", "exec"), globals())
