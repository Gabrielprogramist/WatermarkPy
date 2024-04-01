# WatermarkPy
 This project enables the addition of watermarks to images in various styles, including repeating and centrally placed watermarks. The module is written in Python and uses the Pillow library for image processing.

## Features

- Add a central watermark.
- Add repeating watermarks across the image.
- Customize the style, opacity, color, and size of the watermark text.

## Setup

Before using, ensure you have Python 3.x installed along with all necessary dependencies:

```bash
pip install Pillow
```

You will also need a font for creating the watermark. Place the font file in a font directory at the root of your project.

## Usage

1. Import the Watermarker class from the module.
2. Create an instance of Watermarker, specifying the image path, watermark text, and desired settings.
3. Call the add_watermarks method to add watermarks to the image.
4. Save the result using the save method.

Example code: 
```bash
from watermarker import Watermarker, WatermarkerStyles

watermarker = Watermarker(
    image_path='path_to_your_image/puppy.jpg',
    text='Your Watermark',
    style=WatermarkerStyles.CENTRAL
)
watermarked_image = watermarker.add_watermarks()
watermarker.save('path_for_saving/puppy_watermarked.jpg')
```
