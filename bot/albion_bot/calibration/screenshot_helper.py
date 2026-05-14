"""
Screenshot helper — called as subprocess by Go backend.
Usage: python screenshot_helper.py <x> <y> <w> <h>
Writes PNG bytes to stdout.
"""
import sys
import mss
import mss.tools


def main() -> None:
    if len(sys.argv) != 5:
        sys.stderr.write("Usage: screenshot_helper.py x y w h\n")
        sys.exit(1)

    x, y, w, h = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])

    with mss.mss() as sct:
        mon = {"left": x, "top": y, "width": w, "height": h}
        img = sct.grab(mon)
        png = mss.tools.to_png(img.rgb, img.size)

    sys.stdout.buffer.write(png)


if __name__ == "__main__":
    main()
