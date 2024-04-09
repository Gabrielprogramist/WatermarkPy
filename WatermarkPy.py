import enum
import os
import math
import textwrap
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageChops, ImageOps


class WatermarkerStyles(enum.Enum):
    """стиль водяного знака"""
    # диагональный повтор
    STRIPED = 1
    # центр
    CENTRAL = 2


class Watermarker(object):
    """Инструмент для создания водяных знаков изображения"""

    django_support = False

    def __init__(
            self, image_path: str, text: str,
            style: WatermarkerStyles.STRIPED,
            angle=30,
            color='#936',
            font_file='sample_font.ttf',
            font_height_crop=1.2,
            opacity=0.15,
            quality=80,
            size=50,
            space=75,
            chars_per_line=8,
    ):
        self.image_path = image_path
        self.text = text
        self.style = style
        self.angle = angle
        self.color = color

        if self.django_support:
            from django.conf import settings
            self.font_file = os.path.join(settings.BASE_DIR, 'contrib', 'image', 'font', font_file)
        else:
            self.font_file = os.path.join(os.path.abspath('.'), 'font', font_file)

        self.font_height_crop = font_height_crop
        self.opacity = opacity
        self.quality = quality
        self.size = size
        self.space = space
        self._result_image = None
        self.chars_per_line = chars_per_line

    @staticmethod
    def set_image_opacity(image: Image, opacity: float):
        """Установка прозрачности изображения"""
        assert 0 <= opacity <= 1

        alpha = image.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        image.putalpha(alpha)
        return image

    @staticmethod
    def crop_image_edge(image: Image):
        """Обрезать изображение с пустыми краями"""
        bg = Image.new(mode='RGBA', size=image.size)
        diff = ImageChops.difference(image, bg)
        del bg
        bbox = diff.getbbox()
        if bbox:
            return image.crop(bbox)
        return image

    def _add_mark_striped(self):
        """Добавить диагональный повторяющийся водяной знак"""
        origin_image = Image.open(self.image_path)
        origin_image = ImageOps.exif_transpose(origin_image)

        # Рассчитать ширину и высоту шрифта
        width = len(self.text) * self.size
        height = round(self.size * self.font_height_crop)

        # Создать изображение водяного знака
        watermark_image = Image.new(mode='RGBA', size=(width, height))

        # Создать текст
        draw_table = ImageDraw.Draw(im=watermark_image)
        draw_table.text(
            xy=(0, 0),
            text=self.text,
            fill=self.color,
            font=ImageFont.truetype(self.font_file, size=self.size)
        )
        del draw_table

        # Обрезать пустое пространство
        watermark_image = Watermarker.crop_image_edge(watermark_image)

        # Установить прозрачность
        Watermarker.set_image_opacity(watermark_image, self.opacity)

        # Вычислить длину гипотенузы
        c = int(math.sqrt(origin_image.size[0] * origin_image.size[0] + origin_image.size[1] * origin_image.size[1]))

        watermark_mask = Image.new(mode='RGBA', size=(c, c))

        y, idx = 0, 0
        while y < c:
            x = -int((watermark_image.size[0] + self.space) * 0.5 * idx)
            idx = (idx + 1) % 2

            while x < c:
                watermark_mask.paste(watermark_image, (x, y))
                x = x + watermark_image.size[0] + self.space
            y = y + watermark_image.size[1] + self.space

        watermark_mask = watermark_mask.rotate(self.angle)

        if origin_image.mode != 'RGBA':
            origin_image = origin_image.convert('RGBA')
        origin_image.paste(watermark_mask,  # 大图
            (int((origin_image.size[0] - c) / 2), int((origin_image.size[1] - c) / 2)),  # 坐标
            mask=watermark_mask.split()[3]
        )
        del watermark_mask

        return origin_image

    def _add_mark_central(self):
        """Добавит центрированный водяной знак"""
        origin_image = Image.open(self.image_path)
        origin_image = ImageOps.exif_transpose(origin_image)

        text_lines = textwrap.wrap(self.text, width=self.chars_per_line)
        text = '\n'.join(text_lines)

        width = len(text) * self.size
        height = round(self.size * self.font_height_crop * len(text_lines))

        watermark_image = Image.new(mode='RGBA', size=(width, height))

        draw_table = ImageDraw.Draw(im=watermark_image)
        draw_table.text(
            xy=(0, 0),
            text=text,
            fill=self.color,
            font=ImageFont.truetype(self.font_file, size=self.size)
        )
        del draw_table

        watermark_image = Watermarker.crop_image_edge(watermark_image)

        Watermarker.set_image_opacity(watermark_image, self.opacity)

        c = int(math.sqrt(origin_image.size[0] * origin_image.size[0] + origin_image.size[1] * origin_image.size[1]))
        watermark_mask = Image.new(mode='RGBA', size=(c, c))
        watermark_mask.paste(
            watermark_image,
            (int((watermark_mask.width - watermark_image.width) / 2),
             int((watermark_mask.height - watermark_image.height) / 2))
        )
        # Поворот большого изображения на определенный угол
        watermark_mask = watermark_mask.rotate(self.angle)

        # Добавить водяной знак к исходному изображению
        if origin_image.mode != 'RGBA':
            origin_image = origin_image.convert('RGBA')

        box = (
            int((origin_image.width - watermark_mask.width) / 2),
            int((origin_image.height - watermark_mask.height) / 2))
        origin_image.paste(watermark_mask, box, mask=watermark_mask.split()[3])

        return origin_image

    @property
    def image(self):
        """Получить объект изображения с водяным знаком"""
        if not self._result_image:
            if self.style == WatermarkerStyles.STRIPED:
                self._result_image = self._add_mark_striped()
            if self.style == WatermarkerStyles.CENTRAL:
                self._result_image = self._add_mark_central()
        return self._result_image

    def save(self, file_path: str, image_format: str = 'png'):
        """сохранить изображение"""
        with open(file_path, 'wb') as f:
            self.image.save(f, image_format)

    def show(self):
        self.image.show()

    # Продолжение класса Watermarker

    def _add_multiple_marks(self):
        """Добавить несколько водяных знаков на изображение"""
        origin_image = Image.open(self.image_path)
        origin_image = ImageOps.exif_transpose(origin_image)
        
        watermark_image = self._create_watermark_image()

        # Определение шага размещения водяных знаков по осям X и Y
        step_x = watermark_image.width + self.space
        step_y = watermark_image.height + self.space

        for x in range(0, origin_image.width, step_x):
            for y in range(0, origin_image.height, step_y):
                # Размещение водяного знака на оригинальном изображении
                origin_image.paste(watermark_image, (x, y), watermark_image)

        self._result_image = origin_image

    def _create_watermark_image(self):
        """Создание изображения водяного знака"""
        # Создание текста водяного знака
        text_lines = textwrap.wrap(self.text, width=self.chars_per_line)
        text = '\n'.join(text_lines)
        font = ImageFont.truetype(self.font_file, self.size)
        text_width, text_height = font.getsize_multiline(text)
        
        # Создание изображения для водяного знака
        watermark_image = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark_image)
        draw.multiline_text((0, 0), text, fill=self.color, font=font, spacing=5)
        
        # Применение угла поворота и настройка прозрачности
        watermark_image = watermark_image.rotate(self.angle, expand=1)
        Watermarker.set_image_opacity(watermark_image, self.opacity)

        return watermark_image

    def add_watermarks(self):
        """Добавление множественных водяных знаков на изображение и возвращение результата"""
        if self.style == WatermarkerStyles.STRIPED or self.style == WatermarkerStyles.CENTRAL:
            self._add_multiple_marks()
        return self.image

# Пример использования
if __name__ == '__main__':
    path_to_image = 'puppy.jpg'
    mark_text = 'mark text'
    watermarker = Watermarker(path_to_image, mark_text, WatermarkerStyles.CENTRAL)
    watermarked_image = watermarker.add_watermarks()  # Применить множественные водяные знаки
    watermarked_image.show()  # Показать результат
    watermarker.save('puppy_watermarked.jpg')  


