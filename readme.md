# Installatie

## Installatie van Tesseract OCR

Download de [installer](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v4.1.0.20190314.exe) 
Tesseract OCR 4 en voer deze uit, installeer hierbij het programma voor alle gebruikers. Zorg
er ook voor dat het extra taal pakket voor Nederlands wordt geselecteerd
tijdens de installatie.

Voeg het pad  `C:\Program Files\Tesseract-OCR` toe aan het `Path` systeemvariabel.

Voeg daarna het volgende omgevingsvariabel toe aan het systeem: 
`TESSDATA_PREFIX` met de waarde `C:\Program Files\Tesseract-OCR\tessdata`

## Installatie van Poppler

Download de volgende [zip map](https://github.com/oschwartz10612/poppler-windows/releases/download/v23.08.0-0/Release-23.08.0-0.zip).
Pak deze uit en verplaats de `poppler-23.08.0` map naar de `Program Files` map.

Voeg hierna `C:\Program Files\Tesseract-OCR\poppler-23.08.0\Library\bin` toe aan het `Path` 
systeemvariabel.

## Installatie van DX Drawing OCR

Om de DX drawing OCR te installeren moet het `windows.zip` bestand van de laatste
release gedownload worden. Deze is rechts in het scherm te zien. Hiervan kan dan de inhoudt
in de `C:\Program Files\DXDrawingOCR` map gezet worden. Hierna kan dan een snelkoppeling gemaakt worden.

Als laast, kopieer de inhoudt van de `C:\Program Files\Tesseract-OCR` map naar de `C:\Program Files\DXDrawingOCR\_internal` map.