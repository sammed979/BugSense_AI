const fs = require('fs');
const path = require('path');

// Simple build script to copy files to dist directory
// This prevents Vercel from minifying JavaScript files

const scriptDir = __dirname;
const distDir = path.join(scriptDir, 'dist');

// Create dist directory if it doesn't exist
if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
}

// Copy HTML
fs.copyFileSync(
    path.join(scriptDir, 'index.html'),
    path.join(distDir, 'index.html')
);

// Copy runtime-config.js
fs.copyFileSync(
    path.join(scriptDir, 'runtime-config.js'),
    path.join(distDir, 'runtime-config.js')
);

// Create js directory in dist
const jsDistDir = path.join(distDir, 'js');
if (!fs.existsSync(jsDistDir)) {
    fs.mkdirSync(jsDistDir, { recursive: true });
}

// Copy all JS files
const jsFiles = ['auth.js', 'api.js', 'app.js', 'clipboard.js'];
jsFiles.forEach(file => {
    fs.copyFileSync(
        path.join(scriptDir, 'js', file),
        path.join(jsDistDir, file)
    );
});

// Create css directory in dist
const cssDistDir = path.join(distDir, 'css');
if (!fs.existsSync(cssDistDir)) {
    fs.mkdirSync(cssDistDir, { recursive: true });
}

// Copy CSS
fs.copyFileSync(
    path.join(scriptDir, 'css', 'style.css'),
    path.join(cssDistDir, 'style.css')
);

console.log('Build complete - files copied to dist directory');
