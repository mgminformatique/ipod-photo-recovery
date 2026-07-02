from PIL import Image


def clamp(v):
    return max(0, min(255, int(v)))


def ycbcr_to_rgb(y, cb, cr):
    r = y + 1.402 * (cr - 128)
    g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
    b = y + 1.772 * (cb - 128)
    return clamp(r), clamp(g), clamp(b)


def decode_bluefirst_420(data, width, height, offset=0, order="Y_Cb_Cr"):
    y_size = width * height
    c_width = width // 2
    c_height = height // 2
    c_size = c_width * c_height

    needed = y_size + c_size + c_size
    chunk = data[offset:offset + needed]

    if len(chunk) < needed:
        return None

    y_plane = chunk[:y_size]

    if order == "Y_Cb_Cr":
        cb_plane = chunk[y_size:y_size + c_size]
        cr_plane = chunk[y_size + c_size:y_size + c_size + c_size]
    elif order == "Y_Cr_Cb":
        cr_plane = chunk[y_size:y_size + c_size]
        cb_plane = chunk[y_size + c_size:y_size + c_size + c_size]
    elif order == "Cb_Cr_Y":
        cb_plane = chunk[:c_size]
        cr_plane = chunk[c_size:c_size + c_size]
        y_plane = chunk[c_size + c_size:c_size + c_size + y_size]
    elif order == "Cr_Cb_Y":
        cr_plane = chunk[:c_size]
        cb_plane = chunk[c_size:c_size + c_size]
        y_plane = chunk[c_size + c_size:c_size + c_size + y_size]
    else:
        return None

    img = Image.new("RGB", (width, height))
    pixels = []

    for yy in range(height):
        for xx in range(width):
            y = y_plane[yy * width + xx]
            ci = (yy // 2) * c_width + (xx // 2)
            cb = cb_plane[ci]
            cr = cr_plane[ci]
            pixels.append(ycbcr_to_rgb(y, cb, cr))

    img.putdata(pixels)
    return img
