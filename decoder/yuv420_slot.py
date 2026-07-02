from PIL import Image


def clamp(v):
    return max(0, min(255, int(v)))


def ycbcr_to_rgb(y, cb, cr):
    r = y + 1.402 * (cr - 128)
    g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
    b = y + 1.772 * (cb - 128)
    return clamp(r), clamp(g), clamp(b)


def decode_yuv420_slot(data, width, height, offset=0, cbcr_order="CbCr"):
    """
    iPod-style slot:
    slot size can be width*height*2,
    but useful YCbCr420 data is:
      Y  = width*height
      Cb = width/2 * height/2
      Cr = width/2 * height/2
    """
    y_size = width * height
    c_width = width // 2
    c_height = height // 2
    c_size = c_width * c_height
    needed = y_size + c_size + c_size

    chunk = data[offset:offset + needed]

    if len(chunk) < needed:
        return None

    y_plane = chunk[0:y_size]

    if cbcr_order == "CbCr":
        cb_plane = chunk[y_size:y_size + c_size]
        cr_plane = chunk[y_size + c_size:y_size + c_size + c_size]
    else:
        cr_plane = chunk[y_size:y_size + c_size]
        cb_plane = chunk[y_size + c_size:y_size + c_size + c_size]

    img = Image.new("RGB", (width, height))
    pixels = []

    for y in range(height):
        for x in range(width):
            yy = y_plane[y * width + x]
            ci = (y // 2) * c_width + (x // 2)
            cb = cb_plane[ci]
            cr = cr_plane[ci]
            pixels.append(ycbcr_to_rgb(yy, cb, cr))

    img.putdata(pixels)
    return img
