import os
import torch
import numpy as np
import pytesseract
from ultralytics import YOLO
from transformers import AutoProcessor
from transformers import AutoModelForTokenClassification
from paddleocr import PaddleOCR, draw_ocr
from src.util.utils import normalize_box, unnormalize_box, draw_output, create_json
from PIL import Image

class LayoutLMv3:
    def __init__(self,
                 processor_pretrained='microsoft/layoutlmv3-base',
                 layoutlm_pretrained=os.path.join(
                     'src', 'model', 'models', 'checkpoint'),
                 yolo_pretrained=os.path.join(
                     'src', 'model', 'models', 'best.pt'),
                 tessdata_pretrained=os.path.join('src', 'model', 'models', 'tessdata')):
        self.processor = AutoProcessor.from_pretrained(
            processor_pretrained, apply_ocr=False)
        self.lalm_model = AutoModelForTokenClassification.from_pretrained(
            layoutlm_pretrained)
        self.yolo_model = YOLO(yolo_pretrained)
        self.tess_path = tessdata_pretrained
        self.paddleocr = PaddleOCR(use_angle_cls=False)

    def predict(self, input_img, output_path=None):
        input_image = Image.open(input_img)

        # YOLO
        #bboxes = self.yolo_model.predict(source=input_image, conf=0.3, iou=0.1)[
        #    0].boxes.xyxy.int()

        # paddleocr
        result = self.paddleocr.ocr(input_img, rec=False)

        bboxes = []
        for idx in range(len(result)):
            res = result[idx]
            for line in res:
                # Extract x and y coordinates
                x_coords = [point[0] for point in line]
                y_coords = [point[1] for point in line]

                # Find x1, y1 (minimum x, y) and x2, y2 (maximum x, y)
                x1, y1 = min(x_coords), min(y_coords)
                x2, y2 = max(x_coords), max(y_coords)

                bboxes.append([x1, y1, x2, y2])
                #print(x1, y1, x2, y2)

        #debug paddleocr
        result = result[0]
        image = Image.open(input_img).convert('RGB')
        im_show = draw_ocr(image, result, txts=None, scores=None)
        im_show = Image.fromarray(im_show)
        im_show.save('output/result.jpg')

        mapping_bbox_texts = {}
        texts = []
        normalized_boxes = []
        
        # OCR
        for box in bboxes:
            tlx, tly, brx, bry = int(box[0]), int(
                box[1]), int(box[2]), int(box[3])
            normalized_boxes.append(normalize_box(
                box, input_image.width, input_image.height))
            image_cropped = input_image.crop((tlx-3, tly-3, brx+3, bry+3))
            data = pytesseract.image_to_string(
                image_cropped,
                config=f'--oem 3 --psm 6 --tessdata-dir {self.tess_path}',
                lang='vie',
                output_type=pytesseract.Output.DICT)
            text = data['text'].strip().replace('\n', ' ')
            texts.append(text)
            mapping_bbox_texts[','.join(map(str, normalized_boxes[-1]))] = text
        
        print(mapping_bbox_texts)

        print(texts)

        encoding = self.processor(input_image, texts,
                                  boxes=normalized_boxes,
                                  return_offsets_mapping=True,
                                  return_tensors='pt',
                                  max_length=512,
                                  padding='max_length')
        offset_mapping = encoding.pop('offset_mapping')

        with torch.no_grad():
            outputs = self.lalm_model(**encoding)

        id2label = self.lalm_model.config.id2label
        logits = outputs.logits
        token_boxes = encoding.bbox.squeeze().tolist()
        offset_mapping = offset_mapping.squeeze().tolist()

        predictions = logits.argmax(-1).squeeze().tolist()
        is_subword = np.array(offset_mapping)[:, 0] != 0

        true_predictions = []
        true_boxes = []
        true_texts = []
        for idx in range(len(predictions)):
            if not is_subword[idx] and token_boxes[idx] != [0, 0, 0, 0]:
                true_predictions.append(id2label[predictions[idx]])
                true_boxes.append(unnormalize_box(
                    token_boxes[idx], input_image.width, input_image.height))
                true_texts.append(mapping_bbox_texts.get(
                    ','.join(map(str, token_boxes[idx])), ''))

        if isinstance(output_path, str):
            os.makedirs(output_path, exist_ok=True)
            img_output = draw_output(
                image=input_image,
                true_predictions=true_predictions,
                true_boxes=true_boxes
            )
            img_output.save(os.path.join(output_path, 'result.jpg'))

        return create_json(true_texts, true_predictions, true_boxes)
