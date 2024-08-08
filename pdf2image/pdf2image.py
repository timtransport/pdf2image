"""
    pdf2image is a light wrapper for the poppler-utils tools that can convert your
    PDFs into Pillow images.
"""

import os
import platform
import tempfile
import types
import shutil
import subprocess
import fitz
from subprocess import Popen, PIPE, TimeoutExpired
from typing import Any, Union, Tuple, List, Dict, Callable
from pathlib import PurePath
from PIL import Image

from pdf2image.generators import uuid_generator, counter_generator, ThreadSafeGenerator

from pdf2image.parsers import (
    parse_buffer_to_pgm,
    parse_buffer_to_ppm,
    parse_buffer_to_jpeg,
    parse_buffer_to_png,
)

from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError,
    PDFPopplerTimeoutError,
)

TRANSPARENT_FILE_TYPES = ["png", "tiff"]
PDFINFO_CONVERT_TO_INT = ["Pages"]


def convert_from_path(
    pdf_path: Union[str, PurePath],
    dpi: int = 200,
    output_folder: Union[str, PurePath] = None,
    first_page: int = None,
    last_page: int = None,
    fmt: str = "ppm",
    jpegopt: Dict = None,
    thread_count: int = 1,
    userpw: str = None,
    ownerpw: str = None,
    use_cropbox: bool = False,
    strict: bool = False,
    transparent: bool = False,
    single_file: bool = False,
    output_file: Any = uuid_generator(),
    poppler_path: Union[str, PurePath] = None,
    grayscale: bool = False,
    size: Union[Tuple, int] = None,
    paths_only: bool = False,
    use_pdftocairo: bool = False,
    timeout: int = None,
    hide_annotations: bool = False,
) -> List[Image.Image]:
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    auto_temp_dir = False
    if output_folder is None:
        output_folder = tempfile.mkdtemp()
        auto_temp_dir = True
        
    # Iterate through each page
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        
        # Save the image
        output_path = os.path.join(output_folder, f'page_{page_num + 1}.png')
        pix.save(output_path)

    images = []

        
    if output_folder is not None:
        images += _load_from_output_folder(
            output_folder,
            None,
            'png',
            paths_only,
            in_memory=auto_temp_dir,
        )
        
    return images


def convert_from_bytes(
    pdf_file: bytes,
    dpi: int = 200,
    output_folder: Union[str, PurePath] = None,
    first_page: int = None,
    last_page: int = None,
    fmt: str = "ppm",
    jpegopt: Dict = None,
    thread_count: int = 1,
    userpw: str = None,
    ownerpw: str = None,
    use_cropbox: bool = False,
    strict: bool = False,
    transparent: bool = False,
    single_file: bool = False,
    output_file: Union[str, PurePath] = uuid_generator(),
    poppler_path: Union[str, PurePath] = None,
    grayscale: bool = False,
    size: Union[Tuple, int] = None,
    paths_only: bool = False,
    use_pdftocairo: bool = False,
    timeout: int = None,
    hide_annotations: bool = False,
) -> List[Image.Image]:
    fh, temp_filename = tempfile.mkstemp()
    try:
        with open(temp_filename, "wb") as f:
            f.write(pdf_file)
            f.flush()
            return convert_from_path(
                f.name,
                dpi=dpi,
                output_folder=output_folder,
                first_page=first_page,
                last_page=last_page,
                fmt=fmt,
                jpegopt=jpegopt,
                thread_count=thread_count,
                userpw=userpw,
                ownerpw=ownerpw,
                use_cropbox=use_cropbox,
                strict=strict,
                transparent=transparent,
                single_file=single_file,
                output_file=output_file,
                poppler_path=poppler_path,
                grayscale=grayscale,
                size=size,
                paths_only=paths_only,
                use_pdftocairo=use_pdftocairo,
                timeout=timeout,
                hide_annotations=hide_annotations,
            )
    finally:
        os.close(fh)
        os.remove(temp_filename)


def _parse_jpegopt(jpegopt: Dict) -> str:
    parts = []
    for k, v in jpegopt.items():
        if v is True:
            v = "y"
        if v is False:
            v = "n"
        parts.append("{}={}".format(k, v))
    return ",".join(parts)


def pdfinfo_from_path(
    pdf_path: str,
    userpw: str = None,
    ownerpw: str = None,
    poppler_path: str = None,
    rawdates: bool = False,
    timeout: int = None,
    first_page: int = None,
    last_page: int = None,
) -> Dict:
    """Function wrapping poppler's pdfinfo utility and returns the result as a dictionary.

    :param pdf_path: Path to the PDF that you want to convert
    :type pdf_path: str
    :param userpw: PDF's password, defaults to None
    :type userpw: str, optional
    :param ownerpw: PDF's owner password, defaults to None
    :type ownerpw: str, optional
    :param poppler_path: Path to look for poppler binaries, defaults to None
    :type poppler_path: Union[str, PurePath], optional
    :param rawdates: Return the undecoded data strings, defaults to False
    :type rawdates: bool, optional
    :param timeout: Raise PDFPopplerTimeoutError after the given time, defaults to None
    :type timeout: int, optional
    :param first_page: First page to process, defaults to None
    :type first_page: int, optional
    :param last_page: Last page to process before stopping, defaults to None
    :type last_page: int, optional
    :raises PDFPopplerTimeoutError: Raised after the timeout for the image processing is exceeded
    :raises PDFInfoNotInstalledError: Raised if pdfinfo is not installed
    :raises PDFPageCountError: Raised if the output could not be parsed
    :return: Dictionary containing various information on the PDF
    :rtype: Dict
    """
    try:
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfinterp import resolve1
        
        fp = open(pdf_path, 'rb')

        parser = PDFParser(fp)
        d = PDFDocument(parser)
        info = d.info[0]
        info['Pages'] = int(resolve1(d.catalog['Pages'])['Count'])
        
        return info

    except OSError:
        raise PDFInfoNotInstalledError(
            "Unable to get page count. Is poppler installed and in PATH?"
        )
    except ValueError:
        raise PDFPageCountError(
            f"Unable to get page count.\n{err.decode('utf8', 'ignore')}"
        )


def pdfinfo_from_bytes(
    pdf_bytes: bytes,
    userpw: str = None,
    ownerpw: str = None,
    poppler_path: str = None,
    rawdates: bool = False,
    timeout: int = None,
    first_page: int = None,
    last_page: int = None,
) -> Dict:
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfinterp import resolve1


    parser = PDFParser(pdf_bytes)
    d = PDFDocument(parser)
    info = d.info[0]
    info['Pages'] = int(resolve1(d.catalog['Pages'])['Count'])
    
    return info


def _load_from_output_folder(
    output_folder: str,
    output_file: str,
    ext: str,
    paths_only: bool,
    in_memory: bool = False,
) -> List[Image.Image]:
    images = []
    for f in sorted(os.listdir(output_folder)):
        if f.split(".")[-1] == ext:
            if paths_only:
                images.append(os.path.join(output_folder, f))
            else:
                images.append(Image.open(os.path.join(output_folder, f)))
                if in_memory:
                    images[-1].load()
    return images
