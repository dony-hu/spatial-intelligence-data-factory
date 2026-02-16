# CN1300 地址治理两维测试报告

- 生成时间: 2026-02-15T10:28:49.319380+00:00
- 数据集: testdata/fixtures/lab-mode-phase1_5-中文地址测试用例-1300-2026-02-15.csv
- 样本数: 1300

## 维度一：功能覆盖

- normalize_hit_rate: 0.6
- parse_field_hit_rate: {'province': 1.0, 'city': 1.0, 'district': 1.0, 'road': 0.9, 'house_no': 0.9}
- match_hit_rate: 0.7
- score_judgement_hit_rate: 1.0

## 维度二：城市覆盖

- 上海市: rows=217, normalize=0.599078, match=0.797235, score=1.0
- 北京市: rows=217, normalize=0.599078, match=0.599078, score=1.0
- 武汉市: rows=216, normalize=0.601852, match=0.800926, score=1.0
- 深圳市: rows=217, normalize=0.599078, match=0.801843, score=1.0
- 苏州市: rows=217, normalize=0.603687, match=0.603687, score=1.0
- 随州市: rows=216, normalize=0.597222, match=0.597222, score=1.0

## 效果结论

- 最佳城市(按score命中率): 上海市
- 最低城市(按score命中率): 上海市
- 全局: normalize=0.6, match=0.7, score=1.0
