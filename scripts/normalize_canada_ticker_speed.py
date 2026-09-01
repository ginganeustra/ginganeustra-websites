#!/usr/bin/env python3
"""Keep Canada at War THE TICK moving at one visual speed.

The ticker duplicates its headline set once for a seamless loop. A fixed CSS
animation duration therefore makes the apparent speed change whenever the
headline set gets longer or shorter. This helper installs a tiny client-side
controller that measures one pass of the track and sets the duration from a
constant pixels-per-second target.

During the full Neocities deployment this script also runs the dynamic Canada
at War live-acceptance verifier after the initial upload. The hourly ticker job
does not expose the Neocities API key to this step, so it remains ticker-only.
"""
from pathlib import Path
import os
import re

PAGE = Path("Canada/index.html")
PX_PER_SECOND = 125
MARKER = "ticker-speed-controller"

SCRIPT = f'''<script id="{MARKER}">(function(){{var track=document.querySelector('.ticker-track');if(!track)return;var pxPerSecond={PX_PER_SECOND};function apply(){{var distance=track.scrollWidth/2;if(!distance)return;track.style.animationDuration=(distance/pxPerSecond).toFixed(2)+'s';}}if(document.fonts&&document.fonts.ready)document.fonts.ready.then(apply);else requestAnimationFrame(apply);window.addEventListener('load',apply,{{once:true}});}})();</script>'''


def main() -> int:
    text = PAGE.read_text(encoding="utf-8")
    text, fallback_count = re.subn(
        r"animation:ticker\s+\d+(?:\.\d+)?s\s+linear\s+infinite",
        "animation:ticker 39s linear infinite",
        text,
        count=1,
    )
    if fallback_count != 1:
        raise SystemExit("Could not locate THE TICK fallback animation")

    pattern = rf'<script id="{re.escape(MARKER)}">.*?</script>'
    text, replace_count = re.subn(pattern, SCRIPT, text, count=1, flags=re.S)
    if replace_count == 0:
        if "</body>" not in text:
            raise SystemExit("Could not locate </body> for ticker speed controller")
        text = text.replace("</body>", SCRIPT + "</body>", 1)

    if f"var pxPerSecond={PX_PER_SECOND}" not in text:
        raise SystemExit("Ticker speed controller did not install correctly")

    PAGE.write_text(text, encoding="utf-8")
    print(f"THE TICK speed normalized to {PX_PER_SECOND} px/s based on measured track width.")

    if os.environ.get("NEOCITIES_API_KEY"):
        from verify_canada_live import main as verify_live
        verify_live()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
