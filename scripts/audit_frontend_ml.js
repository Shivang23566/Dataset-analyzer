#!/usr/bin/env node
/**
 * Frontend ML Component Audit Script
 * Analyzes MLBuilderView.tsx and api.ts for ML issues.
 */

const fs = require('fs');

const FINDINGS = [];

function add(severity, category, description, file, line, code, recommendation) {
  FINDINGS.push({ severity, category, description, file, line, code, recommendation });
}

function auditMLBuilder(filePath) {
  if (!fs.existsSync(filePath)) {
    add('CRITICAL', 'FILE_NOT_FOUND', `File not found: ${filePath}`, filePath, 0, '', 'Check path');
    return;
  }
  const source = fs.readFileSync(filePath, 'utf-8');
  const lines = source.split('\n');
  console.log(`\n📄 Auditing: ${filePath} (${lines.length} lines)`);

  // 1. State management
  const hasModelState = source.includes('useState<ModelCard') || source.includes("useState<ModelCard[]");
  if (!hasModelState) {
    add('HIGH', 'NO_MODEL_STATE', 'Model cards not stored in typed state', filePath, 0,
        'Missing useState<ModelCard[]>', 'Store model cards in useState');
  }

  // 2. Check recommendation comparison
  //    recommendation.recommended_model is model ID like "random_forest_classifier"
  //    card.name is display name like "Random Forest"
  //    If comparing recommended_model to card.name, they'll never match!
  const recComparisons = [
    ...source.matchAll(/recommendation\??\.\s*recommended_model\s*===\s*card\.\s*(\w+)/g)
  ];
  for (const m of recComparisons) {
    const field = m[1];
    const lineNum = source.substring(0, m.index).split('\n').length;
    if (field === 'name') {
      add('CRITICAL', 'REC_COMPARES_NAME_NOT_ID',
          'Recommendation compared to card.name instead of card.id! ' +
          'recommended_model returns IDs like "random_forest_classifier" but card.name is "Random Forest". ' +
          'This means AI Pick badge NEVER shows correctly.',
          filePath, lineNum,
          m[0],
          'Change to: recommendation.recommended_model === card.id');
    }
  }

  // 3. Model cards fetched with wrong task (race condition)
  if (source.includes("getModelCards(task ?? 'regression')")) {
    const lineNum = source.indexOf("getModelCards(task ?? 'regression')");
    const ln = source.substring(0, lineNum).split('\n').length;
    add('HIGH', 'WRONG_TASK_FOR_CARDS',
        "Initial model cards fetch uses fallback 'regression' before task detection completes. " +
        "User briefly sees regression models even for classification datasets. " +
        "Although a useEffect re-fetches with correct task, this causes a flash of wrong cards.",
        filePath, ln,
        "getModelCards(task ?? 'regression')",
        "Wait for task detection before fetching cards, or pass the detected task");
  }

  // 4. Math.random
  const randomMatches = [...source.matchAll(/Math\.random\(\)/g)];
  for (const m of randomMatches) {
    const ln = source.substring(0, m.index).split('\n').length;
    add('CRITICAL', 'RANDOM_IN_FRONTEND', 'Math.random() in UI — causes non-deterministic behavior',
        filePath, ln, 'Math.random()', 'Remove random from UI code');
  }

  // 5. Array shuffling
  if (source.includes('.sort(() =>') || source.match(/\.sort\(\s*\(\)\s*=>\s*Math\.random/)) {
    add('HIGH', 'ARRAY_SHUFFLING', 'Array shuffling detected — model options change randomly',
        filePath, 0, '.sort(() => Math.random...)', 'Display models in fixed order');
  }

  // 6. Hardcoded metrics in display
  const hardcoded = source.match(/accuracy.*[:=]\s*["']?0\.\d+|f1.*[:=]\s*["']?0\.\d+/gi);
  if (hardcoded) {
    add('HIGH', 'HARDCODED_DISPLAY', `Hardcoded metric values in display: ${hardcoded[0]}`,
        filePath, 0, hardcoded[0], 'Display metrics from API response only');
  }

  // 7. Missing error handling
  if (!source.includes('catch')) {
    add('MEDIUM', 'NO_ERROR_HANDLING', 'No error handling for API calls',
        filePath, 0, 'Missing catch', 'Add try/catch for API calls');
  }

  // 8. Loading states
  if (!source.includes('Loading') && !source.includes('loading') && !source.includes('Loader')) {
    add('MEDIUM', 'NO_LOADING_STATE', 'No loading indicators for async operations',
        filePath, 0, 'Missing loading state', 'Add loading indicators');
  }

  // 9. useEffect dependency issues — check if model fetching has unstable deps
  const effectBlocks = [...source.matchAll(/useEffect\(\s*\(\)\s*=>\s*\{([\s\S]*?)\}\s*,\s*\[(.*?)\]\s*\)/g)];
  for (const eff of effectBlocks) {
    const body = eff[1];
    const deps = eff[2];
    if (body.includes('getModelCards') && deps.includes('taskInfo')) {
      const ln = source.substring(0, eff.index).split('\n').length;
      add('MEDIUM', 'REFETCH_ON_TASKINFO',
          'useEffect re-fetches model cards when taskInfo changes — this is correct but may cause ' +
          'a brief flash of stale cards between fetches.',
          filePath, ln, `useEffect(..., [${deps}])`,
          'Consider showing loading state during re-fetch');
    }
  }

  // 10. Double fetch of model cards
  const cardsFetchCount = (source.match(/getModelCards\(/g) || []).length;
  if (cardsFetchCount > 1) {
    add('MEDIUM', 'DOUBLE_CARDS_FETCH',
        `getModelCards() called ${cardsFetchCount} times — once in handleTargetChange with wrong task, ` +
        'once in useEffect with correct task. This causes 2 API calls and a flash of wrong models.',
        filePath, 0, `${cardsFetchCount} getModelCards() calls`,
        'Fetch cards only once after task detection completes');
  }

  console.log(`   Found: ${FINDINGS.filter(f => f.file === filePath).length} issues`);
}

function auditApiFile(filePath) {
  if (!fs.existsSync(filePath)) {
    add('CRITICAL', 'FILE_NOT_FOUND', `Not found: ${filePath}`, filePath, 0, '', 'Check path');
    return;
  }
  const source = fs.readFileSync(filePath, 'utf-8');
  console.log(`\n📄 Auditing: ${filePath}`);

  const mlFuncs = ['getMLColumns', 'detectMLTask', 'getMLRecommendation',
                   'getModelCards', 'trainModel', 'getModelDownloadUrl'];
  for (const func of mlFuncs) {
    if (!source.includes(func)) {
      add('MEDIUM', 'MISSING_API_FUNCTION', `Missing ML API function: ${func}`,
          filePath, 0, func, 'Add API function');
    }
  }

  console.log(`   Found: ${FINDINGS.filter(f => f.file === filePath).length} issues`);
}

function auditTypesFile(filePath) {
  if (!fs.existsSync(filePath)) {
    add('MEDIUM', 'FILE_NOT_FOUND', `Not found: ${filePath}`, filePath, 0, '', 'Check path');
    return;
  }
  const source = fs.readFileSync(filePath, 'utf-8');
  console.log(`\n📄 Auditing: ${filePath}`);

  const required = ['MLColumnMeta', 'TaskDetectResponse', 'ModelRecommendation',
                    'ModelCard', 'TrainingResult', 'HyperparmDef'];
  for (const t of required) {
    if (!source.includes(t)) {
      add('MEDIUM', 'MISSING_TYPE', `Missing ML type: ${t}`, filePath, 0, t, 'Add type definition');
    }
  }

  console.log(`   Found: ${FINDINGS.filter(f => f.file === filePath).length} issues`);
}

function printReport() {
  const icons = { CRITICAL: '🔴', HIGH: '🟠', MEDIUM: '🟡', LOW: '🟢' };
  const sevOrder = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  console.log('\n' + '='.repeat(70));
  console.log('🔍 FRONTEND ML AUDIT REPORT');
  console.log('='.repeat(70));

  if (!FINDINGS.length) {
    console.log('\n✅ No issues found!');
    return;
  }

  const bySev = {};
  for (const f of FINDINGS) bySev[f.severity] = (bySev[f.severity] || []).concat(f);

  console.log('\n📊 SUMMARY:');
  console.log('-'.repeat(40));
  for (const sev of sevOrder) {
    const items = bySev[sev] || [];
    if (items.length) console.log(`  ${icons[sev]} ${sev}: ${items.length} issues`);
  }
  console.log(`\n  Total: ${FINDINGS.length} issues`);

  for (const sev of sevOrder) {
    const items = bySev[sev] || [];
    if (!items.length) continue;
    console.log(`\n\n${icons[sev]} ${sev} ISSUES:`);
    console.log('='.repeat(50));
    items.forEach((f, i) => {
      console.log(`\n${i + 1}. [${f.category}]`);
      console.log(`   File: ${f.file}:${f.line}`);
      console.log(`   Issue: ${f.description}`);
      console.log(`   Code: ${f.code}`);
      console.log(`   Fix: ${f.recommendation}`);
    });
  }

  const crit = (bySev['CRITICAL'] || []).length;
  console.log('\n' + '='.repeat(70));
  console.log('🏁 VERDICT:');
  console.log('-'.repeat(40));
  if (crit) {
    console.log(`\n❌ ${crit} CRITICAL frontend issues found that affect ML feature behavior.\n`);
  } else {
    console.log('\n✅ Frontend ML implementation appears functional.\n');
  }
}

// Main
console.log('🔍 Starting Frontend ML Audit...');
auditMLBuilder('frontend/src/components/MLBuilderView.tsx');
auditApiFile('frontend/src/lib/api.ts');
auditTypesFile('frontend/src/lib/types.ts');
printReport();
