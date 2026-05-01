import numpy as np


def rgb_gradient(start_rgb, end_rgb):
    c1 = np.array(start_rgb)
    c2 = np.array(end_rgb)

    steps = yield
    yield
    # linear steps
    t = np.linspace(0, 1, steps)

    # sine-eased parameter (key change)
    t = 0.5 - 0.5 * np.cos(np.pi * t)

    gradient = np.outer(1 - t, c1) + np.outer(t, c2)

    for r, g, b in gradient:
        yield f"\x1b[38;2;{int(r)};{int(g)};{int(b)}m"


RGB_GRADIENT = rgb_gradient((255, 13, 201), (27, 208, 255))
next(RGB_GRADIENT)
