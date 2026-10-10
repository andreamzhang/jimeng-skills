#!/usr/bin/env node
// 资产报告（经典暖金版）结构校验：
//   1. 每个 html 必须引用 ./_shared/js/echarts.min.js
//   2. echarts.init 数 == 图容器 div 数，且每个容器恰好被 init 一次
//   3. 每个图表的 setOption 里必须携带非空 data
// 用法: node tools/check_asset_report.js <report.html> [<report2.html> ...]
const fs = require('fs');

let bad = 0;
for (const file of process.argv.slice(2)) {
  const html = fs.readFileSync(file, 'utf8');
  const refsLocal = html.includes('src="./_shared/js/echarts.min.js"');
  const containers = [...html.matchAll(/id="(c-[a-z0-9-]+)"/g)].map(m => m[1]);
  const inits = [...html.matchAll(/echarts\.init\(/g)];
  const idRefs = [...html.matchAll(/getElementById\('(c-[a-z0-9-]+)'\)/g)].map(m => m[1]);
  const sizes = [...html.matchAll(/(?:type:'pie'|type:'bar'|type:'scatter')[\s\S]{0,400}?data:([^\n]{5,})\}/g)];
  const problems = [];
  if (!refsLocal) problems.push('未引用 ./_shared/js/echarts.min.js');
  const uniq = new Set(containers);
  if (uniq.size !== containers.length) problems.push('容器 id 重复');
  if (containers.length !== inits.length) problems.push(`容器 ${containers.length} != init ${inits.length}`);
  for (const id of containers) {
    if (idRefs.filter(x => x === id).length !== 1) problems.push(`init 使用次数异常: ${id}`);
  }
  if (sizes.length < inits.length) problems.push(`图表 setOption 数疑似不足: ${sizes.length}`);
  const empties = sizes.map(m => m[1]).filter(d => d.includes('[]'));
  if (empties.length) problems.push('存在空 data 图表');
  if (problems.length) { bad++; console.log(`✗ ${file}: ${problems.join(' | ')}`); }
  else console.log(`✓ ${file}: ${containers.length} 容器 / ${inits.length} init / ${sizes.length} data 块`);
}
process.exit(bad ? 1 : 0);
