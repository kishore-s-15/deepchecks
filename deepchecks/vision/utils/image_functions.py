# ----------------------------------------------------------------------------
# Copyright (C) 2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Module for defining functions related to image data."""
import typing as t
import io
import base64

import cv2
import numpy as np
import torch
import PIL.Image as pilimage
import PIL.ImageDraw as pildraw
import PIL.ImageOps as pilops
import plotly.graph_objects as go

from deepchecks.core.errors import DeepchecksValueError
from .detection_formatters import convert_bbox


__all__ = ['ImageInfo', 'numpy_to_image_figure', 'label_bbox_add_to_figure', 'numpy_grayscale_to_heatmap_figure',
           'apply_heatmap_image_properties', 'draw_bboxes', 'prepare_thumbnail', 'crop_image']


class ImageInfo:
    """Class with methods defined to extract metadata about image."""

    def __init__(self, img):
        if not isinstance(img, np.ndarray):
            raise DeepchecksValueError('Expect image to be numpy array')
        self.img = img

    def get_size(self) -> t.Tuple[int, int]:
        """Get size of image as (width, height) tuple."""
        return self.img.shape[1], self.img.shape[0]

    def get_dimension(self) -> int:
        """Return the number of dimensions of the image (grayscale = 1, RGB = 3)."""
        return self.img.shape[2]

    def is_equals(self, img_b) -> bool:
        """Compare image to another image for equality."""
        return np.array_equal(self.img, img_b)


def numpy_to_image_figure(data: np.ndarray):
    """Create image graph object from given numpy array data."""
    dimension = data.shape[2]
    if dimension == 1:
        data = cv2.cvtColor(data, cv2.COLOR_GRAY2RGB)
    elif dimension != 3:
        raise DeepchecksValueError(f'Don\'t know to plot images with {dimension} dimensions')

    return go.Image(z=data, hoverinfo='skip')


def ensure_image(
    image: t.Union[pilimage.Image, np.ndarray, torch.Tensor],
    copy: bool = True
) -> pilimage.Image:
    """Transform to `PIL.Image.Image` if possible.

    Parameters
    ----------
    image : Union[PIL.Image.Image, numpy.ndarray, torch.Tensor]
    copy : bool, default True
        if `image` is an instance of the `PIL.Image.Image` return
        it as it is or copy it.

    Returns
    -------
    `PIL.Image.Image`
    """
    if isinstance(image, pilimage.Image):
        return image.copy() if copy is True else image
    if isinstance(image, torch.Tensor):
        image = t.cast(np.ndarray, image.numpy())
    if isinstance(image, np.ndarray):
        image = image.squeeze()
        if image.ndim == 3:
            return pilimage.fromarray(image)
        elif image.ndim == 2:
            image = image.astype(np.uint8)
            return pilops.colorize(
                pilimage.fromarray(image),
                black='black',
                white='white',
                blackpoint=image.min(),
                whitepoint=image.max(),
            )
        else:
            raise ValueError(f'Do not know how to work with {image.ndim} dimensional images')
    else:
        raise TypeError(f'cannot convert {type(image)} to the PIL.Image.Image')


def draw_bboxes(
    image: t.Union[pilimage.Image, np.ndarray, torch.Tensor],
    bboxes: np.ndarray,
    bbox_notation: t.Optional[str] = None,
    copy_image: bool = True,
    border_width: int = 1,
    color: t.Union[str, t.Dict[np.number, str]] = 'red',
) -> pilimage.Image:
    """Draw bboxes on the image.

    Parameters
    ----------
    image : Union[PIL.Image.Image, numpy.ndarray, torch.Tensor]
        image to draw on
    bboxes : numpy.ndarray
        array of bboxes
    bbox_notation : Optional[str], default None
        format of the provided bboxes
    copy_image : bool, default True
        copy imagge before drawing or not
    border_width : int, default 1
        width of the bbox outline
    color: Union[str, Dict[number, str]], default "red"
        color of the bbox outline. It could be a map mapping class id to the color

    Returns
    -------
    PIL.Image.Image : image instance with drawen bboxes on it
    """
    image = ensure_image(image, copy=copy_image)

    if bbox_notation is not None:
        bboxes = np.array([
            convert_bbox(
                bbox,
                notation=bbox_notation,
                image_width=image.width,
                image_height=image.height,
                _strict=False
            ).tolist()
            for bbox in bboxes
        ])

    draw = pildraw.ImageDraw(image)

    for bbox in bboxes:
        clazz, x0, y0, w, h = bbox
        x1, y1 = x0 + w, y0 + h

        if isinstance(color, str):
            color_to_use = color
        elif isinstance(color, dict):
            color_to_use = color[clazz]
        else:
            raise TypeError('color must be of type - Union[str, Dict[int, str]]')

        draw.rectangle(xy=(x0, y0, x1, y1), width=border_width, outline=color_to_use)
        draw.text(xy=(x0 + (w * 0.5), y0 + (h * 0.2)), text=str(clazz), fill=color_to_use)

    return image


def prepare_thumbnail(
    image: t.Union[pilimage.Image, np.ndarray, torch.Tensor],
    size: t.Optional[t.Tuple[int, int]] = None,
    copy_image: bool = True,
) -> str:
    """Prepare html image tag with the provided image.

    Parameters
    ----------
    image : Union[PIL.Image.Image, numpy.ndarray, torch.Tensor]
        image to use
    size : Optional[Tuple[int, int]], default None
        size to which image should be rescaled
    copy_image : bool, default True
        to rescale the image to the provided size this function uses
        `PIL.Image.Image.thumbnail` method that modified image instance
        in-place. If `copy_image` is set to True image will be copied
        before rescaling.

    Returns
    -------
    str : html '<img>' tag with embedded image
    """
    if size is not None:
        image = ensure_image(image, copy=copy_image)
        image.thumbnail(size=size)
    else:
        image = ensure_image(image, copy=False)

    img_bytes = io.BytesIO()
    image.save(fp=img_bytes, format='PNG')
    img_bytes.seek(0)
    png = base64.b64encode(img_bytes.read()).decode('ascii')
    img_bytes.close()
    return f'<img src="data:image/png;base64,{png}"/>'


def prepare_grid(
    content: t.Union[str, t.Sequence[t.Any]],
    *,
    n_of_rows: t.Optional[int] = None,
    n_of_columns: t.Optional[int] = None,
    style: t.Optional[t.Dict[str, t.Any]] = None
) -> str:
    default_style = {
        'overflow-x': 'auto',
        'display': 'grid',
        'grid-gap': '1.5rem',
        'justify-items': 'center',
        'align-items': 'center',
        'padding': '2rem',
        'width': 'max-content'
    }

    if n_of_rows is not None:
        default_style['grid-template-rows'] = f'repeat({n_of_rows}, 1fr)'
    if n_of_columns is not None:
        default_style['grid-template-columns'] = f'repeat({n_of_rows}, 1fr)'

    if style is not None:
        default_style.update(**style)

    css = ';'.join([
        f'{k}: {v}'
        for k, v in default_style.items()
    ])

    if isinstance(content, str):
        pass
    elif isinstance(content, (list, tuple)):
        content = ''.join([str(it) for it in content])
    else:
        raise TypeError(f'Unsupported data type - {type(content)}')

    return f"""<div class="deepchecks-grid" style="{css}">{content}</div>"""


def numpy_grayscale_to_heatmap_figure(data: np.ndarray):
    """Create heatmap graph object from given numpy array data."""
    dimension = data.shape[2]
    if dimension == 3:
        data = cv2.cvtColor(data, cv2.COLOR_RGB2GRAY)
    elif dimension != 1:
        raise DeepchecksValueError(f'Don\'t know to plot images with {dimension} dimensions')
    return go.Heatmap(z=data.squeeze(), hoverinfo='skip', coloraxis='coloraxis')


def apply_heatmap_image_properties(fig):
    """For heatmap and grayscale images, need to add those properties which on Image exists automatically."""
    fig.update_yaxes(autorange='reversed', constrain='domain')
    fig.update_xaxes(constrain='domain')


def label_bbox_add_to_figure(labels: torch.Tensor, figure, row=None, col=None, color='red',
                             prediction=False):
    """Add a bounding box label and rectangle to given figure."""
    for single in labels:
        if prediction:
            x, y, w, h, _, clazz = single.tolist()
        else:
            clazz, x, y, w, h = single.tolist()
        figure.add_shape(type='rect', x0=x, y0=y, x1=x+w, y1=y+h, row=row, col=col, line=dict(color=color))
        figure.add_annotation(x=x + w / 2, y=y, text=str(clazz), showarrow=False, yshift=10, row=row, col=col,
                              font=dict(color=color))


def crop_image(img: np.ndarray, x, y, w, h) -> np.ndarray:
    """Return the cropped numpy array image by x, y, w, h coordinates (top left corner, width and height."""
    # Convert x, y, w, h to integers if not integers already:
    x, y, w, h = [round(n) for n in [x, y, w, h]]

    # Make sure w, h don't extend the bounding box outside of image dimensions:
    h = min(h, img.shape[0] - y - 1)
    w = min(w, img.shape[1] - x - 1)

    return img[y:y + h, x:x + w]
