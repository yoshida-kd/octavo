# Writes a p-value the usual way: "< .001", ".042".
def format_p(p, digits=3):
    p = float(p)
    if p != p:
        return "NA"
    cut = 10.0 ** -digits
    if p < cut:
        return "< " + f"{cut:.{digits}f}".lstrip("0")
    return f"{p:.{digits}f}".lstrip("0")
