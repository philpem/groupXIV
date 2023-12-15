import math, time, os, argparse, logging, json
from wand.image import Image

parser = argparse.ArgumentParser(
    prog='tile_cutter',
    description='Cuts large images into tiles.')
parser.add_argument('--tile-size', metavar='SIZE', type=int, default=512,
                    help='Tile size (width and height)')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Log debugging information')
parser.add_argument('image', type=argparse.FileType('rb'),
                    help='Source image')
args = parser.parse_args()

if args.verbose:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

layers = []

tile_size = args.tile_size
logging.info("tile size: %dx%d", tile_size, tile_size)

with Image(file=args.image) as source:
    logging.info("image size: %dx%d", source.width, source.height)

    # every zoom level has 2x more tiles
    max_zoom = math.ceil(math.log(max(source.size) / args.tile_size, 2))
    logging.info("zoom levels: 1-%d", max_zoom)

    image_size = args.tile_size * (2 ** max_zoom)
    offset_x, offset_y = tuple((image_size - orig) // 2 for orig in source.size)
    logging.info("tiled size: %dx%d-%d-%d", image_size, image_size, offset_x, offset_y)

    layers.append({
        "name": "???",
        "URL": os.path.basename(args.image.name),
        "width": source.width,
        "height": source.height,
        "tileSize": args.tile_size,
        "imageSize": image_size
    })

    square_source = Image(width=image_size, height=image_size)
    square_source.composite(source,
        (square_source.width - source.width) // 2,
        (square_source.height - source.height) // 2)

for z in range(1, max_zoom + 1):
    source_size = int(args.tile_size * (2 ** (max_zoom - z)))
    logging.info("zoom level %d: source %dx%d", z, source_size, source_size)

    current_image = 0
    total_images = (image_size // source_size) ** 2
    start_time = last_report_time = time.perf_counter()

    for y in range(0, image_size // source_size):
        for x in range(0, image_size // source_size):
            crop_x, crop_y = x * source_size, y * source_size
            path = "%s-tiles/%d/%d/%d.png" % (args.image.name, z, x, y)
            logging.debug("tile %s: source %dx%d%+d%+d",
                          path, source_size, source_size, crop_x, crop_y)

            with square_source.clone() as tile:
                tile.crop(crop_x, crop_y, width=source_size, height=source_size)
                tile.resize(tile_size, tile_size)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tile.save(filename=path)

            current_image += 1
            if time.perf_counter() - last_report_time > 1:
                last_report_time = time.perf_counter()
                eta = (last_report_time - start_time) / current_image * \
                        (total_images - current_image)
                logging.info("completion: %.2f%% (ETA: %dh%dm%ds)",
                             current_image / total_images * 100,
                             eta // 3600, (eta % 3600) // 60, eta % 60)

with open("%s.json" % args.image.name, "w") as descr:
    descr.write(json.dumps({
        "name": "???",
        "scale": None,
        "layers": layers
    }))
    logging.info("image description written to: %s" % descr.name)

logging.info("done")
