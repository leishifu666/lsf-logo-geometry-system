#!/usr/bin/env node
// Optional PNG rasterization. Install sharp locally or resolve via NODE_PATH.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
async function main() {
  const [input, output, widthArg] = process.argv.slice(2);
  if (!input || !output || input === '--help') {
    console.log('Usage: node render_svg.cjs INPUT.svg OUTPUT.png [width-px]');
    return;
  }
  const width = widthArg ? Number(widthArg) : undefined;
  if (width !== undefined && (!Number.isInteger(width) || width<1 || width>12000)) throw Error('width must be 1..12000');
  if (fs.existsSync(output)) throw Error('Output exists: choose a fresh filename');
  fs.mkdirSync(path.dirname(output), {recursive:true});
  let img = sharp(input, {density:144});
  if (width) img = img.resize({width});
  await img.png().toFile(output);
  console.log(output);
}
main().catch(e => {console.error(e.message);process.exitCode=1;});
