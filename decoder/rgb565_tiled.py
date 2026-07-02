from PIL import Image


def rgb565_to_pixels(data, width, height, offset=0):
    need = width * height * 2
    chunk = data[offset:offset + need]

    if len(chunk) < need:
        return None

    pixels = []

    for i in range(0, need, 2):
        value = chunk[i] | (chunk[i + 1] << 8)

        r = ((value >> 11) & 0x1F) << 3
        g = ((value >> 5) & 0x3F) << 2
        b = (value & 0x1F) << 3

        pixels.append((r, g, b))

    return pixels


def save_linear(pixels, width, height, out_path):
    img = Image.new("RGB", (width, height))
    img.putdata(pixels[:width * height])
    img.save(out_path)


def save_tiled(pixels, width, height, tile_w, tile_h, out_path):
    img = Image.new("RGB", (width, height))
    src = 0

    for ty in range(0, height, tile_h):
        for tx in range(0, width, tile_w):
            for y in range(tile_h):
                for x in range(tile_w):
                    px = tx + x
                    py = ty + y

                    if px < width and py < height and src < len(pixels):
                        img.putpixel((px, py), pixels[src])

                    src += 1

    img.save(out_path)


def save_column_tiled(pixels, width, height, tile_w, tile_h, out_path):
    img = Image.new("RGB", (width, height))
    src = 0

    for tx in range(0, width, tile_w):
        for ty in range(0, height, tile_h):
            for y in range(tile_h):
                for x in range(tile_w):
                    px = tx + x
                    py = ty + y

                    if px < width and py < height and src < len(pixels):
                        img.putpixel((px, py), pixels[src])

                    src += 1

    img.save(out_path)
