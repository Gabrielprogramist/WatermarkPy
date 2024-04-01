import enum
import os
import math
import textwrap
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageChops, ImageOps


class WatermarkerStyles(enum.Enum):
    """水印样式"""
    # 斜向重复
    STRIPED = 1
    # 居中
    CENTRAL = 2


class Watermarker(object):
    """图片水印工具"""

    django_support = False

    def __init__(
            self, image_path: str, text: str,
            style: WatermarkerStyles.STRIPED,
            angle=30,
            color='#936',
            font_file='青鸟华光简琥珀.ttf',
            font_height_crop=1.2,
            opacity=0.15,
            quality=80,
            size=50,
            space=75,
            chars_per_line=8,
    ):
        """
        :param image_path:
        :param text: 水印文字
        :param angle: 角度
        :param color: 水印颜色
        :param font_file: 字体文件名
        :param font_height_crop: 水印字体高度裁剪大小（默认即可，按需调整）
        :param opacity: 水印透明度
        :param quality: 图片质量
        :param size: 水印单个文字的大小
        :param space: 水印的间距（仅斜向重复样式有效）
        :param chars_per_line: 每行字数（超过就换行，仅居中水印有效）
        """
        self.image_path = image_path
        self.text = text
        self.style = style
        self.angle = angle
        self.color = color

        # 根据是否Django环境来导入字体文件
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
        # 加了水印的图片
        self._result_image = None
        self.chars_per_line = chars_per_line

    @staticmethod
    def set_image_opacity(image: Image, opacity: float):
        """设置图片透明度"""
        assert 0 <= opacity <= 1

        alpha = image.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        image.putalpha(alpha)
        return image

    @staticmethod
    def crop_image_edge(image: Image):
        """裁剪图片边缘空白"""
        bg = Image.new(mode='RGBA', size=image.size)
        diff = ImageChops.difference(image, bg)
        del bg
        bbox = diff.getbbox()
        if bbox:
            return image.crop(bbox)
        return image

    def _add_mark_striped(self):
        """添加斜向重复水印"""
        origin_image = Image.open(self.image_path)
        origin_image = ImageOps.exif_transpose(origin_image)

        # 计算字体的宽度、高度
        width = len(self.text) * self.size
        height = round(self.size * self.font_height_crop)

        # 创建水印图片
        watermark_image = Image.new(mode='RGBA', size=(width, height))

        # 生成文字
        draw_table = ImageDraw.Draw(im=watermark_image)
        draw_table.text(
            xy=(0, 0),
            text=self.text,
            fill=self.color,
            font=ImageFont.truetype(self.font_file, size=self.size)
        )
        del draw_table

        # 裁剪空白
        watermark_image = Watermarker.crop_image_edge(watermark_image)

        # 设置透明度
        Watermarker.set_image_opacity(watermark_image, self.opacity)

        # 计算斜边长度
        c = int(math.sqrt(origin_image.size[0] * origin_image.size[0] + origin_image.size[1] * origin_image.size[1]))

        # 以斜边长度为宽高创建大图（旋转后大图才足以覆盖原图）用于覆盖在原图之上
        watermark_mask = Image.new(mode='RGBA', size=(c, c))

        # 在大图上生成水印文字
        y, idx = 0, 0
        while y < c:
            # 制造x坐标错位
            x = -int((watermark_image.size[0] + self.space) * 0.5 * idx)
            idx = (idx + 1) % 2

            while x < c:
                # 在该位置粘贴mark水印图片
                watermark_mask.paste(watermark_image, (x, y))
                x = x + watermark_image.size[0] + self.space
            y = y + watermark_image.size[1] + self.space

        # 将大图旋转一定角度
        watermark_mask = watermark_mask.rotate(self.angle)

        # 在原图上添加大图水印
        if origin_image.mode != 'RGBA':
            origin_image = origin_image.convert('RGBA')
        origin_image.paste(watermark_mask,  # 大图
            (int((origin_image.size[0] - c) / 2), int((origin_image.size[1] - c) / 2)),  # 坐标
            mask=watermark_mask.split()[3]
        )
        del watermark_mask

        return origin_image

    def _add_mark_central(self):
        """添加居中水印"""
        origin_image = Image.open(self.image_path)
        origin_image = ImageOps.exif_transpose(origin_image)

        # 针对每行字数对水印文字进行处理
        text_lines = textwrap.wrap(self.text, width=self.chars_per_line)
        text = '\n'.join(text_lines)

        # 计算字体的宽度、高度
        width = len(text) * self.size
        height = round(self.size * self.font_height_crop * len(text_lines))

        # 创建水印图片
        watermark_image = Image.new(mode='RGBA', size=(width, height))

        # 生成文字
        draw_table = ImageDraw.Draw(im=watermark_image)
        draw_table.text(
            xy=(0, 0),
            text=text,
            fill=self.color,
            font=ImageFont.truetype(self.font_file, size=self.size)
        )
        del draw_table

        # 裁剪空白
        watermark_image = Watermarker.crop_image_edge(watermark_image)

        # 设置透明度
        Watermarker.set_image_opacity(watermark_image, self.opacity)

        # 计算斜边长度
        c = int(math.sqrt(origin_image.size[0] * origin_image.size[0] + origin_image.size[1] * origin_image.size[1]))
        # 以斜边长度为宽高创建大图（旋转后大图才足以覆盖原图）用于覆盖在原图之上
        watermark_mask = Image.new(mode='RGBA', size=(c, c))
        watermark_mask.paste(
            watermark_image,
            (int((watermark_mask.width - watermark_image.width) / 2),
             int((watermark_mask.height - watermark_image.height) / 2))
        )
        # 将大图旋转一定角度
        watermark_mask = watermark_mask.rotate(self.angle)

        # 在原图上添加水印
        if origin_image.mode != 'RGBA':
            origin_image = origin_image.convert('RGBA')

        box = (
            int((origin_image.width - watermark_mask.width) / 2),
            int((origin_image.height - watermark_mask.height) / 2))
        origin_image.paste(watermark_mask, box, mask=watermark_mask.split()[3])

        return origin_image

    @property
    def image(self):
        """获取加了水印的图片对象"""
        if not self._result_image:
            if self.style == WatermarkerStyles.STRIPED:
                self._result_image = self._add_mark_striped()
            if self.style == WatermarkerStyles.CENTRAL:
                self._result_image = self._add_mark_central()
        return self._result_image

    def save(self, file_path: str, image_format: str = 'png'):
        """保存图片"""
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


