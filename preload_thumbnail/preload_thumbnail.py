# <div class="placeholder" data-large="https://cdn-images-1.medium.com/max/1800/1*sg-uLNm73whmdOgKlrQdZA.jpeg">
#   <img src="https://cdn-images-1.medium.com/freeze/max/27/1*sg-uLNm73whmdOgKlrQdZA.jpeg?q=20" class="img-small">
#   <div style="padding-bottom: 66.6%;"></div>
# </div>

import os
from subprocess import call, check_output
import logging
import base64
import json

from bs4 import BeautifulSoup
from pelican import signals


logger = logging.getLogger(__name__)


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
                basename = image_local.split("/")[-1]
                thumbnail_local = basename[:basename.rfind(".")] + ".jpg"
                thumbnail_local = os.path.join(settings['OUTPUT_PATH'], os.path.dirname(settings['filenames'][f].save_as), process_dir, thumbnail_local)
                break
        else:
            continue

        image_class = img.get("class", [])
        image_alt = img.get("alt", "")

        noscript = img.wrap(soup.new_tag("noscript"))

        div_tag = soup.new_tag("div")
        div_tag["class"] = image_class + ["placeholder"]
        div_tag["data-large"] = image_source

        noscript.insert_after(div_tag)

        create_thumbnail(image_local, thumbnail_local)
        data_url = "data:image/jpeg;base64," + base64.b64encode(open(thumbnail_local, "rb").read()).decode("utf-8")
        color = get_dominant_color(thumbnail_local)
        div_tag["style"] = "background-color: " + color

        logger.info("Convert {} -> {}B preview ({})".format(basename, len(data_url), color))

        new_img = soup.new_tag("img")
        new_img["src"] = data_url
        new_img["class"] = "img-small"
        new_img["alt"] = image_alt

        # the information of the original image is saved under the thumbnail
        img_width, img_height = get_image_size(thumbnail_local)
        if "icon" not in image_class:
            new_img["width"] = img_width
            new_img["height"] = img_height

        div_tag.append(new_img)

    return str(soup)


def create_thumbnail(infile, outfile):
    if not os.path.exists(outfile) or \
            os.path.getmtime(infile) > os.path.getmtime(outfile):
        path, _ = os.path.split(outfile)
        os.makedirs(path, exist_ok=True)

        # take for gif only first frame
        cmd = ["convert", infile + "[0]", "-scale", "42x42", "-quality", "30", outfile]
        call(cmd)

        obj = {}
        obj["color"] = get_dominant_color(outfile)
        obj["width"], obj["height"] = get_image_size(infile)

        with open(outfile + ".json", "w") as f:
            json.dump(obj, f)


def get_dominant_color(image_file):
    try:
        with open(image_file + ".json") as f:
            j = json.load(f)
            return j["color"]
    except IOError as e:
        print("failed:", e)
        out = check_output(["convert", image_file, "+dither", "-colors", "5", "-define", "histogram:unique-colors=true", "-format", "%c", "histogram:info:"]).decode("utf-8")
        lines = out.split("\n")
        line = sorted(lines)[-1]
        rgb = line.strip().split("#")[1]
        r = rgb[0:2]
        g = rgb[2:4]
        b = rgb[4:6]
        return "#{}{}{}".format(r, g, b)


def get_image_size(image_file):
    try:
        with open(image_file + ".json") as f:
            j = json.load(f)
            return j["width"], j["height"]
    except IOError as e:
        print("failed:", e)
        out = check_output(["convert", image_file, "-print", "%wx%h", "/dev/null"]).decode("utf-8")
        w, h = out.split("x")
        w, h = int(w), int(h)

        return w, h


def register():
    signals.content_written.connect(start_postprocess)


if __name__ == '__main__':
    start_postprocess("test.html", {"filenames": []})
