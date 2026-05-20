import asyncio
import zipfile
import os
import re
import sys
import argparse
from pyppeteer import launch
from urllib.parse import urlparse

def sanitize_filename(name: str) -> str:
    """Remove invalid characters for filenames."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

async def save_mhtml(url: str, output_file: str):
    """Save webpage as MHTML, waiting for possible JS redirects."""
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()
    
    # 1. Navigate and wait for 'load' event first
    await page.goto(url, waitUntil='load')
    
    # 2. Wait a bit for JavaScript redirects to settle
    #    (This is the key part to catch JS-based redirects)
    await page.waitFor(3000)  # Wait 3 seconds for any JS redirect to happen
    
    # 3. Now wait for network to be quiet
    try:
        await page.waitForNavigation(waitUntil='networkidle0', timeout=10000)
    except:
        pass  # No more navigation, that's fine
    
    # 4. Proceed to capture snapshot
    mhtml_data = await page._client.send('Page.captureSnapshot', {})
    with open(output_file, 'wb') as f:
        f.write(mhtml_data['data'].encode())
    await browser.close()

def main():
    parser = argparse.ArgumentParser(description="Download a webpage as MHTML.")
    parser.add_argument("--url", required=True, help="URL of the page to download")
    parser.add_argument("--title", help="Optional title for the output file (without extension)")
    args = parser.parse_args()

    # Determine output filename
    if args.title:
        base_name = sanitize_filename(args.title)
    else:
        parsed = urlparse(args.url)
        path = parsed.path.strip('/').replace('/', '_')
        if path:
            base_name = sanitize_filename(path)
        else:
            base_name = sanitize_filename(parsed.netloc)
        if not base_name:
            base_name = "webpage"

    mhtml_filename = f"{base_name}.mhtml"
    zip_filename = f"{base_name}.zip"

    # Create download directory
    download_dir = "download"
    os.makedirs(download_dir, exist_ok=True)

    # Temporary folder for MHTML
    os.makedirs("temp", exist_ok=True)
    mhtml_path = os.path.join("temp", mhtml_filename)

    print(f"Downloading {args.url} → {mhtml_filename}")
    asyncio.run(save_mhtml(args.url, mhtml_path))

    # Create ZIP inside download folder
    zip_path = os.path.join(download_dir, zip_filename)
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(mhtml_path, arcname=mhtml_filename)

    # Cleanup temp
    import shutil
    shutil.rmtree("temp", ignore_errors=True)

    print(f"✅ Created {zip_path} (contains {mhtml_filename})")

if name == "__main__":
    main()