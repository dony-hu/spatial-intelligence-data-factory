# 空间实体关系图谱 - 快速参考指南

## 🎯 项目目标 - 已完成

✅ 在本地部署SQLite数据库
✅ 导入50个上海地址样本数据
✅ 通过地址治理模块进行结构化拆解
✅ 形成112个节点 + 135条边的空间实体关系图谱
✅ 能够表达7种不同类型的实体关系

---

## 📦 核心组件

### 1. 数据库层 (database/)
```
entity_graph.db          ← SQLite本地数据库 (228 KB)
├─ address_raw_input     原始地址输入
├─ address_parsed        解析后的地址
├─ address_standardized  标准化地址 (包含坐标)
├─ address_entity_mapping 地址→实体映射
├─ address_admin_division 行政划分
├─ entity_node          图谱节点
├─ entity_relationship  图谱关系边
└─ 其他支持表...
```

### 2. 业务逻辑层 (tools/)
```
spatial_entity_graph.py
├─ EntityNode          节点类 (province/city/district/street/poi/address)
├─ EntityRelationship  边类 (7种关系类型)
├─ SpatialEntityGraph  图谱管理器
│  ├─ add_node()
│  ├─ add_relationship()
│  ├─ extract_hierarchical_relationships()
│  ├─ extract_spatial_relationships()
│  ├─ to_json()
│  └─ to_graphml()
└─ 其他辅助方法...

graph_visualizer.py
├─ GraphVisualizer    可视化生成器
├─ generate_nodes_json()
├─ generate_edges_json()
└─ generate_html()    ← 生成交互式HTML
```

### 3. 数据和脚本层
```
testdata/
├─ address_samples_50.py    50个地址数据 (Python格式)
└─ address_samples_50.json  50个地址数据 (JSON格式)

scripts/
├─ build_entity_graph.py    主构建脚本
└─ quickstart_graph.sh      快速启动脚本

output/
├─ entity_relationship_graph.html  交互式可视化 ⭐
├─ graph.json                     JSON图谱
└─ graph.graphml                  GraphML格式
```

---

## 🔄 数据流转流程

```
原始地址数据
    ↓
AddressParser.parse()
    ↓
AddressStandardizer.standardize()
    ↓
EntityMapper.map_to_entity()
    ↓
SpatialEntityGraph 构建图谱
    ├─ 创建节点 (地址、POI、行政区)
    ├─ 提取关系
    │  ├─ 层级关系 (hierarchical)
    │  ├─ 空间关系 (spatial_contains, spatial_adjacent, spatial_near)
    │  └─ 映射关系 (entity_mapping)
    └─ 导出输出
        ├─ JSON
        ├─ GraphML
        └─ HTML可视化
```

---

## 7️⃣ 关系类型详解

| 关系类型 | 说明 | 示例 | 数量 |
|---------|------|------|------|
| **hierarchical** | 层级关系 | 上海市 → 黄浦区 | 11 |
| **spatial_contains** | 空间包含 | 黄浦区 ⊃ 中山东一路 | 50 |
| **spatial_adjacent** | 相邻关系 | 中山东一路 ~ 南京东路 | 0 |
| **spatial_near** | 近邻关系 | 同街道距离<100m的地址 | 24 |
| **entity_mapping** | 实体映射 | 地址 → POI地标 | 50 |
| **multi_source_fusion** | 多源融合 | 多个数据源同一实体 | 0 |
| **data_lineage** | 数据血缘 | raw → parsed → std | 0 |

---

## 💻 使用示例

### 方式1: 快速启动 (推荐)
```bash
bash scripts/quickstart_graph.sh
# 自动构建并生成输出
```

### 方式2: Python脚本
```bash
python3 scripts/build_entity_graph.py
# 控制台输出完整日志
```

### 方式3: 交互式使用
```python
from tools.spatial_entity_graph import SpatialEntityGraph
from database.sqlite_adapter import SQLiteAdapter

# 初始化
graph = SpatialEntityGraph("Shanghai")
adapter = SQLiteAdapter("database/entity_graph.db")

# 添加节点
graph.create_hierarchical_node("310101", "黄浦区", 3)

# 添加关系
graph.add_hierarchical_relationship("3101", "310101")

# 导出
json_data = graph.to_json()
graphml_data = graph.to_graphml()
```

---

## 📊 查询示例

### 数据库查询 (SQLite)
```bash
sqlite3 database/entity_graph.db

# 查看所有标准化地址
SELECT standard_full_address, coordinate_x, coordinate_y
FROM address_standardized LIMIT 10;

# 按区统计地址
SELECT standard_district, COUNT(*) as count
FROM address_standardized
GROUP BY standard_district;

# 查找坐标接近的地址对
SELECT a1.standard_full_address, a2.standard_full_address,
       SQRT(POW(a1.coordinate_x - a2.coordinate_x, 2) +
            POW(a1.coordinate_y - a2.coordinate_y, 2)) as distance
FROM address_standardized a1, address_standardized a2
WHERE a1.id < a2.id AND distance < 0.01
ORDER BY distance;
```

### JSON分析 (Python/jq)
```bash
# 查看图谱统计
jq '.metadata.statistics' output/graph.json

# 获取所有POI节点
jq '.nodes[] | select(.node_type=="poi")' output/graph.json

# 统计关系类型分布
jq '[.edges[] | .relationship_type] | group_by(.) | map({type:.[0], count: length})' output/graph.json

# Python分析
python3 << 'EOF'
import json
with open('output/graph.json') as f:
    g = json.load(f)

# 最高度数节点
from collections import defaultdict
degree = defaultdict(int)
for e in g['edges']:
    degree[e['source_node_id']] += 1
    degree[e['target_node_id']] += 1

top = max(degree, key=degree.get)
print(f"最高度数节点: {top} ({degree[top]})")
EOF
```

---

## 🌐 可视化功能

### 交互式HTML (output/entity_relationship_graph.html)

**操作方式:**
- 🖱️ **拖拽**: 左键点击并拖动节点
- 🔍 **缩放**: 滚轮或触板缩放
- 💡 **详情**: 鼠标悬停显示节点/边详情
- 🎨 **着色**:
  - 节点: 按类型着色 (红=省、橙=市、黄=区、绿=街道、紫=建筑、蓝=POI)
  - 边: 按关系类型着色 (红=层级、蓝=包含、绿=相邻、橙=近邻、紫=映射)

**统计信息:**
- 实时显示节点和边的数量
- 按类型分类的节点/边统计
- 中心度分析 (最高度数节点)

---

## 🔧 常见操作

### 修改地址数据
编辑 `testdata/address_samples_50.py` 中的 `SHANGHAI_SAMPLES` 列表，然后重新运行:
```bash
python3 scripts/build_entity_graph.py
```

### 添加新城市
1. 复制 `address_samples_50.py` 为新文件
2. 修改数据和 `region` 参数
3. 在 `build_entity_graph.py` 中加载新数据

### 导出为其他格式

**Neo4j导入** (需要Neo4j):
```bash
neo4j-import --into database/graph.db --nodes:Node output/graph.graphml
```

**Gephi打开**:
1. 打开 Gephi
2. File → Open → output/graph.graphml
3. 使用Gephi进行布局、分析、导出

**CSV导出** (Python):
```python
import json
with open('output/graph.json') as f:
    g = json.load(f)

# 导出节点为CSV
import csv
with open('nodes.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['id', 'type', 'name', 'level', 'lat', 'lon'])
    w.writeheader()
    for n in g['nodes']:
        w.writerow(n)
```

---

## 🚨 故障排除

### 问题: "ModuleNotFoundError: No module named 'database'"
**解决**: 在项目根目录运行脚本
```bash
cd /Users/01411043/code/spatial-intelligence-data-factory
python3 scripts/build_entity_graph.py
```

### 问题: HTML打不开
**解决**: 使用绝对路径
```bash
open "$(pwd)/output/entity_relationship_graph.html"
```

### 问题: SQLite查询变慢
**解决**: 添加索引
```sql
CREATE INDEX idx_district_coords ON address_standardized(standard_district, coordinate_x, coordinate_y);
```

---

## 📈 性能优化建议

1. **数据库**: 添加更多索引
2. **图谱**: 大规模数据时考虑使用Neo4j
3. **可视化**: 超过1000个节点时使用webgl渲染
4. **查询**: 使用空间索引加速地理查询

---

## 📚 扩展阅读

- **Schema设计**: `database/init_sqlite.py` 中的SQL定义
- **关系类型**: `tools/spatial_entity_graph.py` 中的 `RelationshipType` enum
- **可视化配置**: `tools/graph_visualizer.py` 中的 `NODE_COLORS` 和 `EDGE_STYLES`

---

## 📞 快速联系表

| 功能 | 文件 | 主类 | 主要方法 |
|------|------|------|---------|
| 数据库操作 | database/sqlite_adapter.py | SQLiteAdapter | insert_*, get_* |
| 图谱构建 | tools/spatial_entity_graph.py | SpatialEntityGraph | add_node, add_relationship |
| 可视化 | tools/graph_visualizer.py | GraphVisualizer | generate_html |
| 地址治理 | tools/address_governance.py | AddressGovernanceSystem | process_address |
| 自动化 | scripts/build_entity_graph.py | - | main() |

---

**上次更新**: 2026-02-11
**版本**: 1.0
**状态**: ✅ 生产就绪
