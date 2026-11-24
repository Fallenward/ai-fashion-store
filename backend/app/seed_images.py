from pathlib import Path

OUT = Path(__file__).resolve().parent / "static" / "products"

SILHOUETTES = {
    "top": "M250 250 h300 v360 h-300 z M220 280 h40 v180 h-40 z M540 280 h40 v180 h-40 z",
    "knit": "M270 240 h260 v400 h-260 z M230 270 h50 v160 h-50 z M520 270 h50 v160 h-50 z M340 230 h120 v40 h-120 z",
    "outer": "M240 230 h320 v460 h-320 z M190 260 h60 v240 h-60 z M550 260 h60 v240 h-60 z",
    "dress": "M310 210 h180 v80 h80 v420 h-340 v-420 h80 z",
    "trouser": "M300 220 h200 v80 h-200 z M300 300 h80 v460 h-80 z M420 300 h80 v460 h-80 z",
    "denim": "M280 230 h240 v90 h-240 z M270 320 h110 v450 h-110 z M420 320 h110 v450 h-110 z",
    "shoe": "M180 560 h440 v80 h-80 v40 h-360 z M220 520 h120 v40 h-120 z",
    "accessory": "M300 300 h200 v200 h-200 z M360 250 h80 v50 h-80 z",
}


def write_svg(slug: str, background: str, ink: str, kind: str, label: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    path_d = SILHOUETTES.get(kind, SILHOUETTES["top"])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000" role="img" aria-label="{label}">
  <rect width="800" height="1000" fill="{background}"/>
  <path d="{path_d}" fill="{ink}"/>
  <text x="64" y="920" font-family="Georgia, serif" font-size="28" fill="{ink}" letter-spacing="4">{label}</text>
</svg>
"""
    (OUT / f"{slug}.svg").write_text(svg)
    return f"/static/products/{slug}.svg"
