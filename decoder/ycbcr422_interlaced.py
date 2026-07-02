from PIL import Image


def clamp(v):
    return max(0, min(255, int(v)))


def ycbcr_to_rgb(y, cb, cr):
    r = y + 1.402 * (cr - 128)
    g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
    b = y + 1.772 * (cb - 128)
    return clamp(r), clamp(g), clamp(b)


def decode_interlaced_shared(data, width, height, offset=0, order="Y_Cb_Y_Cr"):
    need = width * height * 2
    chunk = data[offset:offset + need]

    if len(chunk) < need:
        return None

    img = Image.new("RGB", (width, height))
    pixels = []

    for i in range(0, need, 4):
        a, b, c, d = chunk[i], chunk[i + 1], chunk[i + 2], chunk[i + 3]

        if order == "Y_Cb_Y_Cr":
            y0, cb, y1, cr = a, b, c, d
        elif order == "Y_Cr_Y_Cb":
            y0, cr, y1, cb = a, b, c, d
        elif order == "Cb_Y_Cr_Y":
            cb, y0, cr, y1 = a, b, c, d
        elif order == "Cr_Y_Cb_Y":
            cr, y0, cb, y1 = a, b, c, d
        else:
            return None

        pixels.append(ycbcr_to_rgb(y0, cb, cr))
        pixels.append(ycbcr_to_rgb(y1, cb, cr))

    img.putdata(pixels[:width * height])
    return img
