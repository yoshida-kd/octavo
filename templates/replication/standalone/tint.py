# Moves a "#RRGGBB" colour towards white (p = 0 leaves it, p = 1 is white).
def tint(col, p=0.6):
    if isinstance(col, (list, tuple)):
        return [tint(c, p) for c in col]
    h = col.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(c + (255 - c) * p):02X}" for c in rgb)
