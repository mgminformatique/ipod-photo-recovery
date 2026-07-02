from PIL import Image


def bytes_to_rgb888_pixels(data, width, height, offset=0, mode="RGB"):
    need = width * height * 3
    chunk = data[offset:offset + need]

    if len(chunk) < need:
        return None

    pixels = []

    for i in range(0, need, 3):
        a, b, c = chunk[i], chunk[i + 1], chunk[i + 2]

        if mode == "RGB":
            pixels.append((a, b, c))
        else:
            pixels.append((c, b, a))

    return pixels


def linear_image(pixels, width, height):
    img = Image.new("RGB", (width, height))
    img.putdata(pixels[:width * height])
    return img


def tiled_image(pixels, width, height, tile_w, tile_h):
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

    return img


def snake_rows_image(pixels, width, height):
    img = Image.new("RGB", (width, height))
    src = 0

    for y in range(height):
        if y % 2 == 0:
            xs = range(width)
        else:
            xs = range(width - 1, -1, -1)

        for x in xs:
            if src < len(pixels):
                img.putpixel((x, y), pixels[src])
            src += 1

    return img
