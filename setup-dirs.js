#!/usr/bin/env node
/**
 * DataLens Project Setup Script
 *
 * Creates necessary directories and files for the project.
 * Run: node setup-dirs.js
 */

const fs = require('fs');
const path = require('path');

const DIRS_TO_CREATE = [
  // Frontend
  'frontend/src/components',
  'frontend/src/pages',
  'frontend/src/hooks',
  'frontend/src/lib',
  'frontend/src/styles',
  'frontend/src/styles/base',
  'frontend/src/styles/components',
  'frontend/src/styles/features',
  'frontend/src/styles/pages',
  'frontend/src/styles/utilities',
  'frontend/src/types',
  'frontend/public',

  // Backend
  'backend/app/api',
  'backend/app/core',
  'backend/app/models',
  'backend/app/schemas',
  'backend/app/services',
  'backend/app/utils',
  'backend/alembic/versions',
  'backend/test',
  'backend/scripts',
  'backend/static',
  'backend/store',

  // Data directories
  'datasets',
];

const GITKEEP_DIRS = [
  'datasets',
  'backend/store',
  'backend/static/assets',
];

const c = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function log(msg, color = 'reset') {
  console.log(`${c[color]}${msg}${c.reset}`);
}

function main() {
  log('\nDataLens Project Setup', 'blue');
  log('='.repeat(40), 'blue');

  let created = 0;
  let existed = 0;

  log('\nCreating directories...', 'yellow');
  for (const dir of DIRS_TO_CREATE) {
    const full = path.resolve(dir);
    if (!fs.existsSync(full)) {
      fs.mkdirSync(full, { recursive: true });
      log(`  + Created: ${dir}`, 'green');
      created++;
    } else {
      existed++;
    }
  }

  log('\nCreating .gitkeep files...', 'yellow');
  for (const dir of GITKEEP_DIRS) {
    const gk = path.join(dir, '.gitkeep');
    if (fs.existsSync(dir) && !fs.existsSync(gk)) {
      fs.writeFileSync(gk, '');
      log(`  + Created: ${gk}`, 'green');
    }
  }

  log('\n' + '='.repeat(40), 'blue');
  log(`Done! Created ${created} dirs (${existed} already existed)`, 'green');
}

main();

