#!/usr/bin/env node
// checklist-go UserPromptSubmit hook
// Manages per-turn injection of checklist format rules

const fs = require('fs');
const path = require('path');

const configDir = process.env.CLAUDE_CONFIG_DIR ||
  path.join(process.env.HOME || process.env.USERPROFILE, '.claude');
const flagPath = path.join(configDir, '.checklist-go-active');
const counterPath = path.join(configDir, '.checklist-go-counter');

const fullRules = [
  'MUST: CHECKLIST MODE ACTIVE. Format ALL responses as checklist. No paragraphs.',
  '',
  '层级：1. → a.(Tab缩进) → i.(Tab+Tab缩进)',
  '单点 ≤50 字。关键词 **加粗**。一级要点前加 1 个语义相关 emoji。',
  '末尾 #标签（非必需）。代码/命令/表格/安全警告不套清单体。',
  '关闭：/checklist-off 或 "stop checklist"。'
].join('\n');

const reminder = [
  'CHECKLIST MODE ACTIVE. MUST use 1. a. i. format. Example:',
  '',
  '1. 📌 要点',
  '\ta. 说明 #标签'
].join('\n');

try {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => input += chunk);
  process.stdin.on('end', () => {
    const msg = input.toLowerCase();

    // Deactivation
    if (msg.includes('/checklist-off') ||
        msg.includes('stop checklist') ||
        msg.includes('关闭清单体')) {
      try { fs.unlinkSync(flagPath); } catch {}
      try { fs.unlinkSync(counterPath); } catch {}
      console.log('Checklist mode deactivated.');
      process.exit(0);
    }

    // Activation
    if (msg.includes('/checklist-go') ||
        msg.includes('checklist mode') ||
        msg.includes('清单体模式') ||
        msg.includes('开启清单体')) {
      fs.writeFileSync(flagPath, 'active');
      fs.writeFileSync(counterPath, '1');
      console.log(fullRules);
      process.exit(0);
    }

    // Not active — skip
    if (!fs.existsSync(flagPath)) {
      process.exit(0);
    }

    // Active — increment counter, inject based on schedule
    let counter = 1;
    try { counter = parseInt(fs.readFileSync(counterPath, 'utf8')) || 1; } catch {}
    counter++;
    fs.writeFileSync(counterPath, String(counter));

    if (counter % 10 === 1) {
      console.log(fullRules);
    } else {
      console.log(reminder);
    }

    process.exit(0);
  });
} catch {
  process.exit(0);
}
