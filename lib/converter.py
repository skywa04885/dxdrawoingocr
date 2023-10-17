from __future__ import annotations
from pathlib import Path
from PyPDF2 import PdfReader, PageObject, PdfWriter
from pyocr import pyocr
from pdf2image import pdf2image
import logging
import math
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTPage
from time import time, sleep
from PySide6 import QtCore
import re

TITLE_DETECT_CENTER_X = 730.98
TITLE_DETECT_CENTER_Y = 64.752
TITLE_DETECT_TOLERNACE = 15


class TesseractsPdfBuilder(object):
    def __init__(self):
        self.images = []
        self.output_file = None
        self.lang = None
        self.text_only = False

    def set_lang(self, lang):
        self.lang = lang
        return self

    def set_output_file(self, output_file):
        self.output_file = output_file
        return self

    def set_text_only(self, text_only):
        self.text_only = text_only
        return self

    def add_image(self, img):
        self.images.append(img)  # or something else
        return self

    def __validate(self):
        if len(self.images) < 1:
            raise ValueError(
                "At least one image is required to build the pdf!"
            )

        if self.output_file is None:
            raise ValueError("An output-file is required to build the pdf!")

    def build(self):
        '''
        Create and write PDF file.
        '''
        self.__validate()

        handle = pyocr.libtesseract.tesseract_raw.init(lang=self.lang)
        renderer = None
        try:
            pyocr.libtesseract.tesseract_raw.set_page_seg_mode(
                handle, pyocr.libtesseract.tesseract_raw.PageSegMode.SPARSE_TEXT
            )

            renderer = pyocr.libtesseract.tesseract_raw.init_pdf_renderer(
                handle, self.output_file, self.text_only
            )
            assert renderer

            pyocr.libtesseract.tesseract_raw.begin_document(renderer, "")

            for image in self.images:
                pyocr.libtesseract.tesseract_raw.set_image(handle, image)

                # tesseract_raw.set_input_name(handle, input_file)
                pyocr.libtesseract.tesseract_raw.recognize(handle)

                pyocr.libtesseract.tesseract_raw.add_renderer_image(handle, renderer)
            pyocr.libtesseract.tesseract_raw.end_document(renderer)
        finally:
            pyocr.libtesseract.tesseract_raw.cleanup(handle)
            if renderer:
                pyocr.libtesseract.tesseract_raw.cleanup(renderer)


class ConverterUpdateEvent:
    def __init__(self, progress: int, message: str) -> None:
        self.progress = progress
        self.message = message

    def __str__(self):
        return f'{self.progress}: {self.message}'


class ConverterLogEvent:
    def __init__(self, t: float, message: str) -> None:
        self.t = t
        self.message = message

    def __str__(self):
        return f'{self.t}: {self.message}'


class Converter(QtCore.QThread):
    status_signal = QtCore.Signal(ConverterUpdateEvent, name='status')
    log_signal = QtCore.Signal(ConverterLogEvent, name='log')

    def __init__(self, in_file_paths: list[Path], dir_out_path: Path, dir_manual_path: Path, dir_temp_path: Path,
                 dir_finished_path: Path):
        super().__init__()

        # Sets the instance variables.
        self.in_file_paths = in_file_paths
        self.dir_out_path = dir_out_path
        self.dir_manual_path = dir_manual_path
        self.dir_temp_path = dir_temp_path
        self.dir_finished_path = dir_finished_path

        # Sets the state instance variables.
        self.file_index = 0

    @staticmethod
    def build(dir_in_path: Path, dir_out_path: Path, dir_manual_path: Path, dir_temp_path: Path,
              dir_finished_path: Path) -> Converter:
        # Ensures that the input path exists.
        logging.info(f'Checking if {dir_in_path} exists')
        if not dir_in_path.exists():
            raise RuntimeError('Input path does not exist')

        # Ensures that the input path leads to a folder.
        logging.info(f'Checking if {dir_in_path} is directory')
        if not dir_in_path.is_dir():
            raise RuntimeError('Input path is not a directory')

        # Ensures that the output path exists.
        logging.info(f'Ensuring that the output directory {dir_out_path} exists')
        dir_out_path.mkdir(parents=True, exist_ok=True)

        # Ensures that the manual path exists.
        logging.info(f'Ensuring that the manual directory {dir_manual_path} exists')
        dir_manual_path.mkdir(parents=True, exist_ok=True)

        # Ensures that the temp path exists.
        logging.info(f'Ensuring that the temp directory {dir_temp_path} exists')
        dir_temp_path.mkdir(parents=True, exist_ok=True)

        # Ensures that the finished path exists.
        logging.info(f'Ensuring that the finished directory {dir_finished_path} exists')
        dir_finished_path.mkdir(parents=True, exist_ok=True)

        # Gets the paths of all the files in the input directory path.
        logging.info(f'Getting all input file paths from the input directory {dir_in_path}')
        in_file_paths = list(in_file_path for in_file_path in dir_in_path.iterdir() if in_file_path.is_file())
        logging.info(f'Found {len(in_file_paths)} in the input directory {dir_in_path}')

        # Constructs and returns the converter.
        return Converter(in_file_paths, dir_out_path, dir_manual_path, dir_temp_path, dir_finished_path)

    def __emit_log_event(self, message: str) -> None:
        log_event = ConverterLogEvent(time(), message)
        self.log_signal.emit(log_event)

    def __emit_status_event(self, message: str) -> None:
        progress = int(min([100.0, (float(self.file_index) / float(len(self.in_file_paths))) * 100.0])) if len(
            self.in_file_paths) != 0 else 100
        status_event = ConverterUpdateEvent(progress, message)
        self.status_signal.emit(status_event)

    def __run_perform_ocr_on_pdf(self, in_file_path: Path) -> Path:
        # Obtains the images from the PDF file.
        self.__emit_status_event(f'Obtaining images from PDF file {in_file_path}')
        self.__emit_log_event(f'Obtaining images from PDF file {in_file_path}')
        pdf_images = pdf2image.convert_from_path(in_file_path, dpi=200, fmt='jpg')

        # Constructs the PDF builder.
        pdf_builder = TesseractsPdfBuilder()

        # Loops over all the pdf images and rotates them so they're aligned
        #  properly. Then adds them to the PDF builder.
        for pdf_image_index, pdf_image in enumerate(pdf_images):
            # Detects the orientation of the document.
            self.__emit_status_event(f'Detecting orientation of page {pdf_image_index} from file {in_file_path}')
            try:
                angle = pyocr.libtesseract.detect_orientation(pdf_image, lang='nld')['angle']
                self.__emit_log_event(f'Detected orientation of angle {angle} for page {pdf_image_index}')
            except pyocr.libtesseract.TesseractError:
                angle = 0
                self.__emit_log_event(f'Orientation detection failed for page {pdf_image_index}')

            # Rotates the image based on the detected angle.
            self.__emit_log_event(f'Rotating page {pdf_image_index} by angle {angle}')
            self.__emit_status_event(f'Rotating page {pdf_image_index} from file {in_file_path} by {angle}')
            pdf_image = pdf_image.rotate(angle, expand=True)

            # Adds the page to the output pdf.
            self.__emit_log_event(f'Adding page {pdf_image_index} to output pdf')
            pdf_builder.add_image(pdf_image)

        # Builds the PDF file.
        self.__emit_status_event(f'Performing OCR on file {in_file_path}')
        temp_file_path = self.dir_temp_path / f'{in_file_path.stem}'
        pdf_builder.set_output_file(str(temp_file_path))
        pdf_builder.set_lang('nld')
        pdf_builder.build()

        # Finishes off and returns the path with the file ending with the PDF extension.
        self.__emit_log_event(
            f'Finished OCR for file with path {in_file_path}, wrote OCR\'ed file to path {temp_file_path}')
        return temp_file_path.with_suffix('.pdf')

    def __process_page(self, temp_file_page_index: int, temp_file_reader_page: PageObject,
                       temp_file_page: LTPage) -> None:
        project_nr = None
        drawing_nr = None

        # Gets all the text elements.
        self.__emit_log_event(f'Getting all text elements in page')
        text_elements = [e for e in temp_file_page if isinstance(e, LTTextContainer)]
        self.__emit_log_event(f'Found {len(text_elements)} text elements on page {temp_file_page_index} of pdf file')

        # Loops over all the text elements.
        self.__emit_log_event(f'Attempting to find title of document')
        for text_element in text_elements:
            # Computes the center of the element.
            element_center_x = (text_element.x1 - text_element.x0) / 2 + text_element.x0
            element_center_y = (text_element.y1 - text_element.y0) / 2 + text_element.y0

            # Computes the distance between the centers.
            element_center_dist = math.sqrt(
                math.pow(element_center_x - TITLE_DETECT_CENTER_X, 2) + math.pow(
                    element_center_y - TITLE_DETECT_CENTER_Y, 2))
            if element_center_dist > TITLE_DETECT_TOLERNACE:
                continue

            # Gets the text from the element.
            title = text_element.get_text()

            # Attempts to get the project number and the drawing number from the title.
            match = re.search(r'([0-9]+)\.([0-9.]+)', title)
            if match is not None:
                # Gets the project number and the drawing number.
                project_nr = match.group(1)
                drawing_nr = match.group(2)

                # Prints that we detected the project and drawing number.
                self.__emit_log_event(
                    f'Detected project number {project_nr} and drawing number {drawing_nr} for '
                    f'page {temp_file_page_index}')

                # Writes the page to the appropriate file.
                self.__write_succeeded_page(project_nr, drawing_nr, temp_file_reader_page)
            else:
                self.__emit_log_event(f'Failed to detect title for page {temp_file_page_index}')

            # We found the element, so just exit.
            break

        # Checks to which path the output page should be written.
        if project_nr is not None and drawing_nr is not None:
            self.__write_succeeded_page(project_nr, drawing_nr, temp_file_reader_page)
        else:
            self.__write_failed_page(temp_file_reader_page)

    def __process_temp_file(self, temp_file_path: Path) -> None:
        # Opens the temp file.
        self.__emit_log_event(f'Opening temp file {temp_file_path}')
        with temp_file_path.open('rb') as temp_file:
            # Reads the temp file.
            self.__emit_log_event(f'Reading temp file {temp_file_path}')
            temp_file_reader = PdfReader(temp_file)
            temp_file_pages = extract_pages(temp_file_path)

            # Processes all the pages.
            for temp_file_page_index, (temp_file_reader_page, temp_file_page) in enumerate(
                    zip(temp_file_reader.pages, temp_file_pages)):
                self.__process_page(temp_file_page_index, temp_file_reader_page, temp_file_page)

    def __clear_temp_files(self) -> None:
        self.__emit_log_event('Clearing temp files')
        for temp_file in self.dir_temp_path.iterdir():
            self.__emit_log_event(f'Unlinking temp file {temp_file}')
            temp_file.unlink()

    def run(self) -> None:
        # Allows progress animation.
        sleep(0.5)

        # Processes all the input files.
        for (in_file_path_index, in_file_path) in enumerate(self.in_file_paths):
            self.file_index = in_file_path_index
            temp_file_path = self.__run_perform_ocr_on_pdf(in_file_path)
            self.__process_temp_file(temp_file_path)
            self.__move_finished_file(in_file_path)

        # Sets the file index to the length to indicate we've processed all.
        self.file_index = len(self.in_file_paths)

        # Clears the temp files.
        self.__clear_temp_files()

        # Emits the event indicating we're finished.
        self.__emit_status_event('Finished')

    def __move_finished_file(self, in_file_path: Path):
        new_in_file_path = self.dir_finished_path / in_file_path.name
        self.__emit_log_event(f'Moving in file {in_file_path} to {new_in_file_path}')
        in_file_path.rename(new_in_file_path)

    def __write_failed_page(self, page: PageObject) -> None:
        # Creates the file path.
        file_path = self.dir_manual_path / f'{time()}.pdf'

        # Creates a new pdf writer and adds a page.
        pdf_writer = PdfWriter()
        pdf_writer.add_page(page)

        # Writes the output to the file path.
        with open(file_path, 'wb') as tertiary_file:
            pdf_writer.write(tertiary_file)

    def __write_succeeded_page(self, project_no: str, drawing_no: str, page: PageObject) -> None:
        # Creates the directory path and the file path.
        secondary_dir_path = (self.dir_out_path / f'{project_no[0:2]}{"".join("X" for _ in range(len(project_no) - 2))}'
                              / project_no)
        tertiary_file_path = secondary_dir_path / f'{project_no}.{drawing_no}.pdf'

        # Makes the directory and it's parents for the output file.
        secondary_dir_path.mkdir(parents=True, exist_ok=True)

        # Creates a new pdf writer and adds a page.
        pdf_writer = PdfWriter()
        pdf_writer.add_page(page)

        # Writes the pdf to the file at the tertiary file path.
        with open(tertiary_file_path, 'wb') as tertiary_file:
            pdf_writer.write(tertiary_file)
