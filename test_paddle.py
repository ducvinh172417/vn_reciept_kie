from paddleocr import PaddleOCR, draw_ocr
ocr = PaddleOCR() # need to run only once to download and load model into memory
img_path = 'mcocr_public_145014onmxs.jpg'
result = ocr.ocr(img_path,rec=False)

i = 0
txt = []
for idx in range(len(result)):
    res = result[idx]
    for line in res:
        i += 1
        txt.append(f"{i}")
        # Extract x and y coordinates
        x_coords = [point[0] for point in line]
        y_coords = [point[1] for point in line]

        # Find x1, y1 (minimum x, y) and x2, y2 (maximum x, y)
        x1, y1 = min(x_coords), min(y_coords)
        x2, y2 = max(x_coords), max(y_coords)

        print(x1, y1, x2, y2)

# draw result
from PIL import Image
result = result[0]
image = Image.open(img_path).convert('RGB')
im_show = draw_ocr(image, result, txts=None, scores=None)
im_show = Image.fromarray(im_show)
im_show.save('output/result.jpg')