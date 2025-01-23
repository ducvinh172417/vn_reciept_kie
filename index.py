import os
import random
from PIL import Image
import streamlit as st
import json
from src.util.transforms import Transforms
from src.model.layoutlmv3 import LayoutLMv3



def init_models():
    extractor = LayoutLMv3()
    return extractor


extractor = init_models()


uploaded_file = "mcocr_public_145014onmxs.jpg"

result = extractor.predict(uploaded_file, "output")

if result:
    print(result)
    with open('extracted_data.json', 'w') as f:
        json.dump(result, f, indent=4)
    print("Exported extracted data to extracted_data.json")
#result = extractor.predict(bin_image.convert('RGB'))