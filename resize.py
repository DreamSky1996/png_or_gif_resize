from PIL import Image
import urllib.request
import io
import time
import argparse

from numpy import number

g_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
g_fetch_data_retry_count = 3


def get_data_from_url(url):
    retry_count = 0
    while True:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": g_user_agent})
            with urllib.request.urlopen(req) as u:
                f = io.BytesIO(u.read())
                if retry_count:
                    print("Retry count", retry_count)
                return f
        except Exception as e:
            if retry_count == g_fetch_data_retry_count:
                print("Failed to fetch data from ", url)
                return None
            retry_count += 1
            time.sleep(3)

def resize_gif(data, save_as, resize_to=None):
    """
    Resizes the GIF to a given length:

    Args:
        path: the path to the GIF file
        save_as (optional): Path of the resized gif. If not set, the original gif will be overwritten.
        resize_to (optional): new size of the gif. Format: (int, int). If not set, the original GIF will be resized to
                              half of its size.
    """
    all_frames = extract_and_resize_frames(data, resize_to)
    print (len(all_frames))

    if len(all_frames) == 1:
        print("Warning: only 1 frame found")
        all_frames[0].save(save_as, optimize=True)
    else:
        all_frames[0].save(save_as, optimize=True, save_all=True, append_images=all_frames[1:], loop=1000)

def resize_png(data, save_as, resize_to=None):
    im = Image.open(data)
    if not resize_to:
        resize_to = (im.size[0] // 2, im.size[1] // 2)
    im = im.resize(resize_to)
    im.save(save_as , format="WebP")


def analyseImage(data):
    """
    Pre-process pass over the image to determine the mode (full or additive).
    Necessary as assessing single frames isn't reliable. Need to know the mode
    before processing all frames.
    """
    im = Image.open(data)
    results = {
        'size': im.size,
        'mode': 'full',
    }
    try:
        while True:
            if im.tile:
                tile = im.tile[0]
                update_region = tile[1]
                update_region_dimensions = update_region[2:]
                if update_region_dimensions != im.size:
                    results['mode'] = 'partial'
                    break
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return results


def extract_and_resize_frames(data, resize_to=None):
    """
    Iterate the GIF, extracting each frame and resizing them

    Returns:
        An array of all frames
    """
    mode = analyseImage(data)['mode']
    print(mode)

    im = Image.open(data)
    print(im.info)

    if not resize_to:
        resize_to = (im.size[0] // 2, im.size[1] // 2)

    i = 0
    p = im.getpalette()
    last_frame = im.convert('RGBA')

    all_frames = []

    try:
        while True:
            # print("saving %s (%s) frame %d, %s %s" % (path, mode, i, im.size, im.tile))

            '''
            If the GIF uses local colour tables, each frame will have its own palette.
            If not, we need to apply the global palette to the new frame.
            '''
            if not im.getpalette():
                im.putpalette(p)

            new_frame = Image.new('RGBA', im.size)

            '''
            Is this file a "partial"-mode GIF where frames update a region of a different size to the entire image?
            If so, we need to construct the new frame by pasting it on top of the preceding frames.
            '''
            if mode == 'partial':
                new_frame.paste(last_frame)

            new_frame.paste(im, (0, 0), im.convert('RGBA'))
            new_frame.thumbnail(resize_to, Image.ANTIALIAS)
            all_frames.append(new_frame)

            i += 1
            if mode != 'partial':
                last_frame = new_frame
            im.seek(im.tell() + 1)
    except EOFError:
        pass

    return all_frames

def is_gif(data):
    im = Image.open(data)
    is_png = im.is_animated
    return is_png

def resize_gif_and_png(data, save_as, resize_to=None):
    is_gif_flag = is_gif(data)

    if is_gif_flag:
        resize_gif(data, save_as + ".gif", resize_to)
    else:
        resize_png(data, save_as + ".png", resize_to)

def resize_from_url(url, size):
    data_gif = get_data_from_url(url)
    resize_gif_and_png(data_gif, "1-out", size)
    


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url", type=str, help="image url")
    ap.add_argument("w", help="new image width")
    ap.add_argument("h",  help="new image height")
    args = vars(ap.parse_args())
    url = args.get('url')
    w = int(args.get('w'))
    h = int(args.get('h'))

    resize_from_url(url, (w,h))
