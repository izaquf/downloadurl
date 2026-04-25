#
#	@uthor izaquf
#	Python
#
#	Download files via URL

# pip install requests beautifulsoup4

import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
from textwrap import wrap
import argparse
import tempfile
import time

# Display Settings
MAXLINEWIDTH = 70
FILELISTWIDTH = 60

def pHeader(title):
	print("\n" + "=" * MAXLINEWIDTH)
	print(f" {title} ".center(MAXLINEWIDTH, " "))
	print("=" * MAXLINEWIDTH)

def pFooter():
	print("=" * MAXLINEWIDTH)

def decodeUrlFileName(url):
	decodeUrl = unquote(url)
	replacements = {
	"%20": ' ',
	"%C3%A1": 'á',
	"%C3%A9": 'é',
	"%C3%AD": 'í',
	"%C3%B3": 'ó',
	"%C3%BA": 'ú',
	"%C3%A3": 'ã',
	"%C3%A2": 'â',
	"%C3%AA": 'ê',
	"%C3%B5": 'õ',
	"%C3%A7": 'ç'
	}
	fileName = decodeUrl.split('/')[-1]
	for code, char in replacements.items():
		fileName = fileName.replace(code, char)
	return fileName

def SafeDownloadFile(url, savePath):
	# Download individual file
	tempPath = f"{savePath}.tmp"
	fileName = os.path.basename(savePath)

	try:
		print(f"⌛ Downloading: {fileName[:FILELISTWIDTH]}{'...' if len(fileName) > FILELISTWIDTH else ''}")

		# If the file already exists
		rsmBytePos = os.path.getsize(tempPath) if os.path.exists(tempPath) else 0

		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
		}
		if rsmBytePos > 0:
			print(f"↻ Resuming interrupted download: {rsmBytePos/1024/1024:.1f} MB")
			headers['Range'] = f'bytes={rsmBytePos}-'

		maxTimeOut = 3

		for attempt in range(maxTimeOut):
			try:
				rsp = requests.get(url, stream=True, timeout=120, headers=headers)
				rsp.raise_for_status()
				break
			except requests.exceptionsTimeout:
				if attempt == (maxTimeOut - 1):
					raise
				print(f"⌛ Timeout, trying again ({attempt + 1}/{maxTimeOut})...")
				time.sleep(5)

		tSize = int(rsp.headers.get('content-length', 0)) + rsmBytePos
		download = rsmBytePos

		# The 'ab' mode is used to add files in case of resumption, and 'wb' for a new download
		mode = 'ab' if rsmBytePos > 0 else 'wb'

		with open(tempPath, mode) as f:
			for chunk in rsp.iter_content(chunk_size=8192):
				if chunk:
					f.write(chunk)
					download+=len(chunk)
					if tSize > 0:
						progress = int(50 * download / tSize)
						sys.stdout.write(f"\r[{'=' * progress}{' ' * (50 - progress)}] {download/1024/1024:.1f} MB")
						sys.stdout.flush()

		sys.stdout.write("\n")

		# If the complete download
		if tSize > 0 and download < tSize:
			raise Exception(f"Incomplete download: {download/tSize} bytes")

		# Rename the temporary file to the final name
		os.replace(tempPath, savePath)
		print(f"✓ Completed: {fileName[:FILELISTWIDTH]}{'...' if len(fileName) > FILELISTWIDTH else ''}")
		return True

	except KeyboardInterrupt:
		print(f"\n\n[CTRL] + [C]\n")
		if os.path.exists(tempPath):
			os.remove(tempPath)
		sys.exit(1)

	except requests.exceptions.RequestException as error:
		print(f"\n✗ Error when downloading: {fileName} -> {str(error)}")
		if os.path.exists(tempPath):
			os.remove(tempPath)
		return False

	except Exception as error:
		print(f"\n✗ Unexpected error: {str(error)}")
		if os.path.exists(tempPath):
			os.remove(tempPath)
		return False

def getAllFiles(url, extensions=None):
	# Retrieves all file links from the webpage; allows filtering by specific extensions, if provided
	try:
		print(f"\n🔍 Analyzing URL: {url}")
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
		}
		maxTimeOut = 3

		for attempt in range(maxTimeOut):
			try:
				rsp = requests.get(url, stream=True, timeout=120, headers=headers)
				rsp.raise_for_status()
				break
			except requests.exceptionsTimeout:
				if attempt == (maxTimeOut - 1):
					raise
				print(f"⌛ Timeout, trying again ({attempt + 1}/{maxTimeOut})...")
				time.sleep(5)

		soup = BeautifulSoup(rsp.text, 'html.parser')
		files = []

		for link in soup.find_all('a', href=True):
			href= link['href']
			if not href or href.startswith('#'):
				continue
			fullUrl = urljoin(url, href)
			fileName = href.split('/')[-1]

			if '.' in fileName:
				ext = fileName.split('.')[-1].lower()
				if extensions is None or ext in extensions:
					files.append(fullUrl)

		return list(set(files)) # Remove duplicate URLs

	except requests.exceptions.RequestException as error:
		print(f"✗ Error accessing URL: {str(error)}")
		return []
			
	except Exception as error:
		print(f"✗ An unexpected error occurred while parsing the page: {str(error)}")
		return []

def displayFileList(files):
	# Displays a formatted list of available files
	if not files:
		print("No files found for download")
		return False

	pHeader(f"📁 Files available for download ({len(files)})")

	for i, fileUrl in enumerate(files, 1):
		fileName = decodeUrlFileName(fileUrl)
		wrappedLines = wrap(f"{i:>3}. {fileName}", width=FILELISTWIDTH)
		for line in wrappedLines:
			print(line)

	pFooter()

def downloadFiles(files, outputDir):
	# Manages the file download process
	os.makedirs(outputDir, exist_ok=True)
	tFiles = len(files)
	successCount = 0
	skippedCount = 0
	failedCount = 0

	print(f"\n⏳ Starting the download of {tFiles} files to: {outputDir}\n")

	for fileUrl in files:
		fileName = decodeUrlFileName(fileUrl)
		savePath = os.path.join(outputDir, fileName)

		if os.path.exists(savePath):
			print(f"⚠ Existing file: {fileName[:FILELISTWIDTH]}{'...' if len(fileName) > FILELISTWIDTH else ''} (skipping)")
			skippedCount+=1
			continue

		if SafeDownloadFile(fileUrl, savePath):
			successCount+=1
		else:
			failedCount+=1

	return {
		'total' : tFiles,
		'success' : successCount,
		'skipped' : skippedCount,
		'failed' : failedCount
	}

def pSummary(stats):
	# Displays a formatted summary of the download process
	pHeader("Download Summary")

	print(f"• Total available files: {stats['total']}")
	print(f"• Files downloaded successfully: {stats['success']}")
	print(f"• Files that already existed: {stats['skipped']}")
	if stats['failed'] > 0:
		print(f"• Files with download errors: {stats['failed']}")    
	pFooter()
	print("\n✅ Completed!\n")
	return stats

def cleanTmpFiles(outputDir):
	# Remove the temporary file from the output directory
	tempFiles = [f for f in os.listdir(outputDir) if f.endswith('.tmp')]
	if tempFiles:
		print(f"\n🔍 Clearing temporary files")
		for tempFile in tempFiles:
			try:
				os.remove(os.path.join(outputDir, tempfile))
				print(f"✓ Removed: {tempfile}")
			except Exception as error:
				print(f"✗ Error removing: {tempfile} -> {str(error)}")

def usage():
	print(r"""
Usage: downloadurl.py [-h]

Download files via URL

Commands:
	-o            Default directory for saving files: downloads
	-t            Filter by specific file extensions, for example, zip, pdf
	-swf          View the list of files before downloading

Example:
	python downloadurl.py https://example.com/files/
	python downloadurl.py https://example.com/ -t zip rar -o myFile
	python downloadurl.py https://example.com/ -swf
	""")

def main():
	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)

	parse = argparse.ArgumentParser(description="Download files from URL")

	parse.add_argument('url', help='URL containing the files for download')
	parse.add_argument('-o', default='downloads', help='Default directory for saving files: downloads')
	parse.add_argument('-t', nargs='*', help='Filter by specific file extensions, for example, zip, pdf')
	parse.add_argument('-swf', action='store_true', help='View the list of files before downloading')

	args = parse.parse_args()

	# Extensions, if provided
	exts = [ext.lower().strip('.') for ext in args.t] if args.t else None

	# File list
	files = getAllFiles(args.url, exts)

	# Show list
	if args.swf:
		displayFileList(files)
		print(f"\nCompleted")
	else:
		stats = downloadFiles(files, args.o)
		cleanTmpFiles(args.o)
		pSummary(stats)

if __name__ == "__main__":
	main()
