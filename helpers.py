from wand.image import Image
from wand.display import display
import os

def make_thumbnail(directory, system_uid, size=100, overwrite=False):
    src_filename = "%s.jpg" % system_uid
    src_path = os.path.join(directory, src_filename)
    suffix = 'jpg'
    if not os.path.exists(src_path):
        src_filename = "%s.png" % system_uid
        src_path = os.path.join(directory, src_filename)
        suffix = 'png'

    with Image(filename=src_path) as img:
        w, h = img.size
        offset_x = 0
        offset_y = 0
        if w > h:
            factor = h / float(size)
            new_h = size
            new_w = int(w / factor)
            offset_x = int((new_w - size) / 2)
        else:
            factor = w / size
            new_w = size
            new_h = int(h / factor)
            offset_y = int((new_h - size) / 2)

        img.resize(int(new_w), int(new_h))
        img.crop(left=offset_x, top=offset_y, width=size, height=size)
        thumb_filename = system_uid + '_thumb.' + suffix
        thumb_path = os.path.join(directory, thumb_filename)
        if overwrite or not os.path.exists(thumb_path):
            img.save(filename=thumb_path)
        elif os.path.exists(thumb_path):
            print "can't overwrite existing file"
