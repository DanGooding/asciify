
import argparse
from PIL import Image
from math import floor, ceil
import os

def to_chars(im, args):
    """ convert im to text, one character per pixel

        returns a list of rows
    """
    # ensure this is single channel (greyscale)
    im = im.convert('L')

    # aspect ratio of a character when its displayed 
    # (they aren't perfect squares like pixels)
    # height / width
    char_aspect = 2

    # result size in characters
    width = args.width
    height = int(im.height / im.width * width / char_aspect)

    downscaled = im.resize((width, height))

    # tonemap so darkest char for min_lum
    #       and lightest char for max_lum
    min_lum, max_lum = im.getextrema()

    pixels = list(downscaled.getdata())

    if args.shade:
        levels = ' ░▒▓█'
    elif args.custom_levels is not None:
        levels = args.custom_levels
    else:
        levels = ' +#'

    if args.invert:
        levels = levels[::-1]

    rows = []
    for y in range(height):
        char_row = []
        for x in range(width):
            luminance = pixels[x + y * width]
            level_index = floor((luminance - min_lum) / (max_lum + 1 - min_lum) * len(levels))
            char_row.append(levels[level_index])
        
        rows.append(''.join(char_row))

    return rows


def to_chars_superpixels(im, args):
    """ convert im to text, using braille characters
        each of which samples multiple times

        returns a list of rows
    """
    # ensure this is single channel greyscale
    im = im.convert('L')

    # samples per pixel (ratio of these is assumed char aspect ratio)
    # 2,4 for full 8 dot braille, or 2,3 for 6 dot braille
    horiz_samples = 2
    vert_samples = 4

    # scale down to desired size
    pixels_across = args.width
    subpixel_width = im.width / (pixels_across * horiz_samples)
    pixels_down = im.height / (subpixel_width * vert_samples) # may not be an integer

    downscaled = im.resize(
        (int(pixels_across * horiz_samples), 
        int(pixels_down * vert_samples)))

    pixels_down = ceil(pixels_down)

    # tonemap so darkest char for min_lum
    #       and lightest char for max_lum
    min_lum, max_lum = im.getextrema()

    pixels = list(downscaled.getdata())

    # the empty braille character has this unicode value
    # rest are offset from this
    base_code = 0x2800
    # 0 3  least significant bit controls top left etc.
    # 1 4
    # 2 5
    # 6 7
    bit_index = lambda dx, dy: dx * 3 + dy if dy < 3 else dx + 6

    rows = []
    for y in range(pixels_down):
        char_row = [] 
        for x in range(pixels_across):
            
            offset = 0
            for dx in range(horiz_samples):
                for dy in range(vert_samples):
                    i = (x * horiz_samples + dx + 
                        (y * vert_samples + dy) * pixels_across * horiz_samples)
                    
                    if i < len(pixels):
                        luminance = pixels[i]
                        bit = round((luminance - min_lum) / (max_lum - min_lum))
                    else:
                        # off the bottom - blank
                        continue

                    if args.invert:
                        bit = 1 - bit

                    offset |= bit << bit_index(dx, dy)
            
            char = chr(base_code + offset)
            char_row.append(char)
        rows.append(''.join(char_row))

    return rows


if __name__ == '__main__':
        
    parser = argparse.ArgumentParser(description='convert an image to ascii art')
    parser.add_argument('source', 
        help='path to the source image')
    parser.add_argument('width', 
        type=int, 
        help='output width in characters')
    parser.add_argument('-i', '--invert', 
        action='store_true', 
        help=(
            'invert colors to look right for black text on a white background. '
            'by default looks correct for white text on a black background'))

    style = parser.add_mutually_exclusive_group()
    style.add_argument('--ascii', action='store_true',
        help='style using basic ascii characters (the default)')
    style.add_argument('--shade', action='store_true',
        help='style using shaded block characters')
    style.add_argument('--dots', action='store_true',
        help='style using braille characters for higher resolution')
    style.add_argument('--custom', 
        dest='custom_levels',
        metavar='LEVELS',
        action='store',
        default=None,
        help=(
            'specify your own sequence of characters to be used, '
            'from most empty to most filled. e.g " .~*#"'))

    parser.add_argument('-s', '--save', 
        dest='output_path', 
        metavar='PATH', 
        nargs='?',
        action='store',
        const='',
        default=None,
        help=(
            'write the result to a file, rather than stdout. '
            'if no path is specified, `source` is used, but with the `.txt` extension'))

    args = parser.parse_args()
    source_path = args.source

    im = Image.open(source_path)
    original_width, original_height = im.size

    if im.mode == 'RGBA': 
        # don't know what RGB values transparent pixels will have,
        # to control this, blend with an opaque single color background image
        background_color = (255, 255, 255) if args.invert else (0, 0, 0)
        background_image = Image.new('RGBA', im.size, color=background_color + (255,))
        im = Image.alpha_composite(background_image, im)
        im.convert('RGB')

    if args.dots:
        rows = to_chars_superpixels(im, args)
    else:
        rows = to_chars(im, args)

    if args.output_path is None:
        for row in rows:
            print(row)

    else:
        output_path = args.output_path
        if output_path == '':
            base_path, _ = os.path.splitext(source_path)
            output_path = base_path + '.txt'
        
        with open(output_path, 'wb') as f:
            f.writelines((row + os.linesep).encode('utf-8') for row in rows)
        
        print(f'saved to {output_path}')
