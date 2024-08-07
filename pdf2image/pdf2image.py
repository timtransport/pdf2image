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
    """Function wrapping pdftoppm and pdftocairo

    :param pdf_path: Path to the PDF that you want to convert
    :type pdf_path: Union[str, PurePath]
    :param dpi: Image quality in DPI (default 200), defaults to 200
    :type dpi: int, optional
    :param output_folder: Write the resulting images to a folder (instead of directly in memory), defaults to None
    :type output_folder: Union[str, PurePath], optional
    :param first_page: First page to process, defaults to None
    :type first_page: int, optional
    :param last_page: Last page to process before stopping, defaults to None
    :type last_page: int, optional
    :param fmt: Output image format, defaults to "ppm"
    :type fmt: str, optional
    :param jpegopt: jpeg options `quality`, `progressive`, and `optimize` (only for jpeg format), defaults to None
    :type jpegopt: Dict, optional
    :param thread_count: How many threads we are allowed to spawn for processing, defaults to 1
    :type thread_count: int, optional
    :param userpw: PDF's password, defaults to None
    :type userpw: str, optional
    :param ownerpw: PDF's owner password, defaults to None
    :type ownerpw: str, optional
    :param use_cropbox: Use cropbox instead of mediabox, defaults to False
    :type use_cropbox: bool, optional
    :param strict: When a Syntax Error is thrown, it will be raised as an Exception, defaults to False
    :type strict: bool, optional
    :param transparent: Output with a transparent background instead of a white one, defaults to False
    :type transparent: bool, optional
    :param single_file: Uses the -singlefile option from pdftoppm/pdftocairo, defaults to False
    :type single_file: bool, optional
    :param output_file: What is the output filename or generator, defaults to uuid_generator()
    :type output_file: Any, optional
    :param poppler_path: Path to look for poppler binaries, defaults to None
    :type poppler_path: Union[str, PurePath], optional
    :param grayscale: Output grayscale image(s), defaults to False
    :type grayscale: bool, optional
    :param size: Size of the resulting image(s), uses the Pillow (width, height) standard, defaults to None
    :type size: Union[Tuple, int], optional
    :param paths_only: Don't load image(s), return paths instead (requires output_folder), defaults to False
    :type paths_only: bool, optional
    :param use_pdftocairo: Use pdftocairo instead of pdftoppm, may help performance, defaults to False
    :type use_pdftocairo: bool, optional
    :param timeout: Raise PDFPopplerTimeoutError after the given time, defaults to None
    :type timeout: int, optional
    :param hide_annotations: Hide PDF annotations in the output, defaults to False
    :type hide_annotations: bool, optional
    :raises NotImplementedError: Raised when conflicting parameters are given (hide_annotations for pdftocairo)
    :raises PDFPopplerTimeoutError: Raised after the timeout for the image processing is exceeded
    :raises PDFSyntaxError: Raised if there is a syntax error in the PDF and strict=True
    :return: A list of Pillow images, one for each page between first_page and last_page
    :rtype: List[Image.Image]
    """

    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # Iterate through each page
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        
        # Save the image
        output_path = os.path.join(output_folder, f'page_{page_num + 1}.png')
        # pix.save(output_path)

    images = []

    auto_temp_dir = False
    if output_folder is None:
        output_folder = tempfile.mkdtemp()
        auto_temp_dir = True
        
    if output_folder is not None:
        images += _load_from_output_folder(
            output_folder,
            None,
            'png',
            paths_only,
            in_memory=auto_temp_dir,
        )


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
    """Function wrapping pdftoppm and pdftocairo.

    :param pdf_bytes: Bytes of the PDF that you want to convert
    :type pdf_bytes: bytes
    :param dpi: Image quality in DPI (default 200), defaults to 200
    :type dpi: int, optional
    :param output_folder: Write the resulting images to a folder (instead of directly in memory), defaults to None
    :type output_folder: Union[str, PurePath], optional
    :param first_page: First page to process, defaults to None
    :type first_page: int, optional
    :param last_page: Last page to process before stopping, defaults to None
    :type last_page: int, optional
    :param fmt: Output image format, defaults to "ppm"
    :type fmt: str, optional
    :param jpegopt: jpeg options `quality`, `progressive`, and `optimize` (only for jpeg format), defaults to None
    :type jpegopt: Dict, optional
    :param thread_count: How many threads we are allowed to spawn for processing, defaults to 1
    :type thread_count: int, optional
    :param userpw: PDF's password, defaults to None
    :type userpw: str, optional
    :param ownerpw: PDF's owner password, defaults to None
    :type ownerpw: str, optional
    :param use_cropbox: Use cropbox instead of mediabox, defaults to False
    :type use_cropbox: bool, optional
    :param strict: When a Syntax Error is thrown, it will be raised as an Exception, defaults to False
    :type strict: bool, optional
    :param transparent: Output with a transparent background instead of a white one, defaults to False
    :type transparent: bool, optional
    :param single_file: Uses the -singlefile option from pdftoppm/pdftocairo, defaults to False
    :type single_file: bool, optional
    :param output_file: What is the output filename or generator, defaults to uuid_generator()
    :type output_file: Any, optional
    :param poppler_path: Path to look for poppler binaries, defaults to None
    :type poppler_path: Union[str, PurePath], optional
    :param grayscale: Output grayscale image(s), defaults to False
    :type grayscale: bool, optional
    :param size: Size of the resulting image(s), uses the Pillow (width, height) standard, defaults to None
    :type size: Union[Tuple, int], optional
    :param paths_only: Don't load image(s), return paths instead (requires output_folder), defaults to False
    :type paths_only: bool, optional
    :param use_pdftocairo: Use pdftocairo instead of pdftoppm, may help performance, defaults to False
    :type use_pdftocairo: bool, optional
    :param timeout: Raise PDFPopplerTimeoutError after the given time, defaults to None
    :type timeout: int, optional
    :param hide_annotations: Hide PDF annotations in the output, defaults to False
    :type hide_annotations: bool, optional
    :raises NotImplementedError: Raised when conflicting parameters are given (hide_annotations for pdftocairo)
    :raises PDFPopplerTimeoutError: Raised after the timeout for the image processing is exceeded
    :raises PDFSyntaxError: Raised if there is a syntax error in the PDF and strict=True
    :return: A list of Pillow images, one for each page between first_page and last_page
    :rtype: List[Image.Image]
    """

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
    """Function wrapping poppler's pdfinfo utility and returns the result as a dictionary.

    :param pdf_bytes: Bytes of the PDF that you want to convert
    :type pdf_bytes: bytes
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
    :return: Dictionary containing various information on the PDF
    :rtype: Dict
    """
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
