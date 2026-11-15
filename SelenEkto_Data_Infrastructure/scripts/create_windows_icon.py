"""Make a Windows .ico from your assets/branding/logo.png without modifying PNG."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
source = root/'assets'/'branding'/'logo.png'
if not source.is_file():
    raise SystemExit('Missing logo.png in assets/branding; add your own square PNG first.')
with Image.open(source) as original:
    icon = original.convert('RGBA')
    icon.save(root/'assets'/'branding'/'logo.ico', format='ICO',
              sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Created assets/branding/logo.ico for Windows executable branding.')
