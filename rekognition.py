import io
import boto3
from PIL import Image
import imagehash
import shelve

class RekognitionHelper():
    def __init__(self, size, shelve_file = None):
        self.client = boto3.client('rekognition', region_name='us-west-2')      # us-west-2 (Oregon) is much cheaper than Sydney!
        self.size = size
        if shelve_file:
            print('Persistent image hash store: {}'.format(shelve_file))
            self._hash_labels = shelve.open(shelve_file, 'c')
        else:
            self._hash_labels = {}

    def get_labels(self, file_name, ignore_labels = [], only_labels = [], with_instances = True, min_confidence = 90):
        image = Image.open(file_name)

        image_hash = str(imagehash.phash(image))
        if image_hash in self._hash_labels:
            return { 'labels': self._hash_labels[image_hash], 'mode': 'imagehash', 'hash': image_hash }

        thumb = image.copy()
        thumb.thumbnail(self.size, Image.ANTIALIAS)

        thumb_io = io.BytesIO()
        thumb.save(thumb_io, 'JPEG')
        thumb_io.seek(0)

        response = self.client.detect_labels(
            Image={
                'Bytes': thumb_io.read()
            },
            MaxLabels=10,
            MinConfidence=min_confidence,
        )

        labels = response['Labels']

        if ignore_labels:
            labels = [label for label in labels if label['Name'] not in ignore_labels]

        if only_labels:
            labels = [label for label in labels if label['Name'] in only_labels]

        if with_instances:
            labels = [label for label in labels if label['Instances']]

        self._hash_labels[image_hash] = labels

        if type(self._hash_labels) == shelve.DbfilenameShelf:
            # This only makes sense when we use 'shelve'
            self._hash_labels.sync()

        return { 'labels': labels, 'mode': 'rekognition', 'hash': image_hash }

    def _tmp_get_boxes():
        for label in response['Labels']:
            if not label['Instances']:
                continue
            print("Label: " + label['Name'])
            print("Confidence: " + str(label['Confidence']))
            print("Instances:")
            for instance in label['Instances']:
                #print("  Bounding box")
                #print("    Top: " + str(instance['BoundingBox']['Top']))
                #print("    Left: " + str(instance['BoundingBox']['Left']))
                #print("    Width: " +  str(instance['BoundingBox']['Width']))
                #print("    Height: " +  str(instance['BoundingBox']['Height']))
                print("  Confidence: " + str(instance['Confidence']))
                print()

                crop_pix = (
                    im.width * instance['BoundingBox']['Left'],
                    im.height * instance['BoundingBox']['Top'],
                    im.width * (instance['BoundingBox']['Left'] + instance['BoundingBox']['Width']),
                    im.height * (instance['BoundingBox']['Top'] + instance['BoundingBox']['Height'])
                )
                im_crop = im.crop(crop_pix)
                im_pyg = pygame.image.fromstring(im_crop.tobytes(), im_crop.size, im_crop.mode)
                display.fill(display_bgcolour)
                display.blit(im_pyg, (
                    (display_width - im_crop.width) / 2,
                    (display_height - im_crop.height) / 2
                ))
                pygame.display.flip()
                time.sleep(2)

            print("----------")
            print()
