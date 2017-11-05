# <div class="placeholder" data-large="https://cdn-images-1.medium.com/max/1800/1*sg-uLNm73whmdOgKlrQdZA.jpeg">
#   <img src="https://cdn-images-1.medium.com/freeze/max/27/1*sg-uLNm73whmdOgKlrQdZA.jpeg?q=20" class="img-small">
#   <div style="padding-bottom: 66.6%;"></div>
# </div>

import os
from subprocess import call
import collections

from bs4 import BeautifulSoup
from pelican import signals


Path = collections.namedtuple(
    'Path', ['base_url', 'source', 'base_path', 'filename', 'process_dir']
)


def start_postprocess(path, context):
    if 'IMAGE_PROCESS_DIR' not in context:
        context['IMAGE_PROCESS_DIR'] = 'thumbnails'

    with open(path, 'r+') as f:
        res = replace_images(f, context)
        f.seek(0)
        f.truncate()
        f.write(res)


def replace_images(f, settings):
    process_dir = settings['IMAGE_PROCESS_DIR']

    soup = BeautifulSoup(f, "html.parser")

    for img in soup.find_all("img"):
        image_source = img["src"]
        url_path, filename = os.path.split(image_source)

        for f in settings['filenames']:
            if os.path.basename(img['src']) in f:
                image_local = settings['filenames'][f].source_path
                thumbnail_local = image_local.split("/")[-1]
                thumbnail_local = thumbnail_local[:thumbnail_local.rfind(".")] + ".jpg"
                thumbnail_url = os.path.join(url_path, process_dir, thumbnail_local)
                thumbnail_local = os.path.join(settings['OUTPUT_PATH'], os.path.dirname(settings['filenames'][f].save_as), process_dir, thumbnail_local)
                break
        else:
            thumbnail_local = image_source + ".thumb"
            image_local = image_source
            thumbnail_url = image_source + ".thumb"

        image_class = img.get("class", [])
        image_alt = img.get("alt", "")

        noscript = img.wrap(soup.new_tag("noscript"))

        div_tag = soup.new_tag("div")
        div_tag["class"] = "placeholder"
        div_tag["data-large"] = image_source

        noscript.insert_after(div_tag)

        new_img = soup.new_tag("img")
        new_img["src"] = thumbnail_url
        new_img["class"] = image_class + ["img-small"]
        new_img["alt"] = image_alt

        placeholder = soup.new_tag("div")
        placeholder["style"] = "padding-bottom: 200px;"

        div_tag.append(new_img)
        div_tag.append(placeholder)

        create_thumbnail(image_local, thumbnail_local)

    return str(soup)


def create_thumbnail(infile, outfile):
    path, _ = os.path.split(outfile)
    os.makedirs(path, exist_ok=True)

    # take for gif only first frame
    cmd = ["convert", infile+"[0]", "-scale", "50x50", outfile]

    if not os.path.exists(outfile) or \
            os.path.getmtime(infile) > os.path.getmtime(outfile):
        print(" ".join(cmd))
        call(cmd)


def register():
    signals.content_written.connect(start_postprocess)


if __name__ == '__main__':
    start_postprocess("test.html", {"filenames": []})
