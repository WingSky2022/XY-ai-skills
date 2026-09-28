# build · 工作台构建与自检

## 构建（JSON 注入）

```bash
python3 - <<'EOF'
import json
data = open('capability_data.json', encoding='utf-8').read()
json.loads(data)                      # 先校验 JSON 合法
tpl = open('workbench-template.html', encoding='utf-8').read()
assert '__DATA_JSON__' in tpl
open('index.html', 'w', encoding='utf-8').write(tpl.replace('__DATA_JSON__', data))
print('构建完成')
EOF
```

要点：
- 数据与模板**同源注入**——不要让页面 fetch 外部 JSON（`file://` 下必被 CORS 拦，双击打开会白屏）。
- 注入前 `json.loads` 校验；改数据 = 改 JSON 后重新构建，产物可随时重建。

## 自检清单（交付前逐条过）

1. **静态**：JS 可解析（`node --check` 或等价手段）；无外部 `<script src>`/CDN/字体链；`getElementById` 目标 id 全存在。
2. **交互**：默认角证据面板已填充；周期律默认「使用说明」已填充；点击角/格子能切换面板。
3. **响应式**：≤820px bento 单列、周期律容器可横向滚动、无横向溢出；无「初始空白面板」。
4. **空数据防御**：任一数组为空时页面不抛错（模板 JS 均为 map 渲染，空数组自然空态）。
5. **截图目检**：六角无重叠、圆点第二行、借假修真标签不密集。
6. 数据源同源性：`index.html` 内嵌 JSON 与磁盘 JSON 逐字节一致（构建即保证）。
