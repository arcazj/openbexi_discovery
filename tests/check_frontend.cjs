// Compile inline JavaScript without running it or requiring a browser.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
let count = 0;
for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
  const attributes = match[1];
  if (/\bsrc\s*=/i.test(attributes) || /\btype\s*=\s*["'](?:application\/ld\+json|application\/json)["']/i.test(attributes)) continue;
  new vm.Script(match[2], {filename: `index.html:inline-script-${++count}`});
}
if (!count) throw new Error('No inline application script was found.');
new vm.Script(fs.readFileSync(path.join(__dirname, '..', 'assets', 'discovery.js'), 'utf8'), {filename: 'assets/discovery.js'});
new vm.Script(fs.readFileSync(path.join(__dirname, '..', 'assets', 'data.js'), 'utf8'), {filename: 'assets/data.js'});
new vm.Script(fs.readFileSync(path.join(__dirname, '..', 'assets', 'captions.js'), 'utf8'), {filename: 'assets/captions.js'});
new vm.Script(fs.readFileSync(path.join(__dirname, '..', 'assets', 'customize.js'), 'utf8'), {filename: 'assets/customize.js'});
new vm.Script(fs.readFileSync(path.join(__dirname, '..', 'assets', 'profile_ai.js'), 'utf8'), {filename: 'assets/profile_ai.js'});
new vm.Script(fs.readFileSync(path.join(__dirname, '..', 'assets', 'ai_progress.js'), 'utf8'), {filename: 'assets/ai_progress.js'});
console.log(`Frontend syntax verified: ${count} inline script(s).`);
