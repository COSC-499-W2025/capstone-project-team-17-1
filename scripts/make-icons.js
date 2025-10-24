// scripts/make-icons.js
const fs = require('fs');
const path = require('path');
const iconGen = require('icon-gen');

(async () => {
  const outDir = path.resolve('build');
  const srcPng = path.join(outDir, 'icon.png');

  if (!fs.existsSync(srcPng)) {
    console.error('build/icon.png missing. Run: npm run icon:png');
    process.exit(1);
  }

  fs.mkdirSync(outDir, { recursive: true });

  try {
    const results = await iconGen(srcPng, outDir, {
      modes: ['ico', 'icns'], // generate both formats
      report: true            // log what it made
    });
    console.log('✓ Generated icons:', results);
  } catch (err) {
    console.error('Icon generation failed:', err);
    process.exit(1);
  }
})();
