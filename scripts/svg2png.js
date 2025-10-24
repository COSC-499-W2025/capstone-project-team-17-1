// scripts/svg2png.js
const fs = require('fs');
const sharp = require('sharp');

(async () => {
  fs.mkdirSync('build', { recursive: true });

  // Rasterize your SVG to a crisp, transparent 1024×1024 PNG
  await sharp('assets/loom-icon.svg', { density: 512 })
    .resize(1024, 1024, { fit: 'contain', background: { r:0, g:0, b:0, alpha:0 } })
    .png()
    .toFile('build/icon.png');

  console.log('✓ Wrote build/icon.png');
})();
