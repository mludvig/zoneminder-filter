import io
import boto3
from PIL import Image
import imagehash

class RekognitionHelper():
    def __init__(self, size):
        self.client = boto3.client('rekognition')
        self.size = size
        self._last_image_hash = ""
        self._last_labels = []

    def get_labels(self, file_name, only_labels = [], with_instances = True, min_confidence = 90):
        image = Image.open(file_name)

        image_hash = str(imagehash.phash(image))
        if image_hash == self._last_image_hash:
            print("    # %s -- same image hash" % file_name)
            return self._last_labels

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

        if only_labels:
            labels = [label for label in labels if label['Name'] in only_labels]

        if with_instances:
            labels = [label for label in labels if label['Instances']]

        self._last_image_hash = image_hash
        self._last_labels = labels

        return labels

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
