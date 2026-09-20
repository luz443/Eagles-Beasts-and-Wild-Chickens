# 研究复盘工作台改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 打通结构化条件、证据链与验证闭环，并交付可公开访问的高端研究复盘工作台。

**Architecture:** 契约层新增可选 `conditions`；网页用共享条件工具读取结构化数据，视图层增加概览、证据和验证状态，路由保留深链能力。静态站点继续零后端依赖，发布使用临时公共隧道。

**Tech Stack:** 原生 HTML/CSS/ES modules、Python unittest、Node 脚本、静态 HTTP。

**Spec:** `docs/superpowers/specs/2026-09-20-research-workbench-design.md`

## Global Constraints

- 保留暖纸背景、朱砂强调和档案刊语言。
- 网页不调用模型；语义判断继续由 LearnBuddy 专家完成。
- 结构化条件缺失时显示“未提供”，不从自然语言自动猜测。
- 原始判断追加保留，人工反驳不覆盖原档案。

### Task 1: 统一结构化条件契约

**Files:** `contracts/record.schema.json`, `src/rra/contracts/models.py`, `src/rra/contracts/validator.py`, `web/js/contracts.js`, `web/data/library.sample.json`, `data/library.seed.json`, `web/js/util/conditions.js`

- [x] 增加可选 `conditions` 字段及九维校验。
- [x] 为样例档案补齐条件值。
- [x] 添加网页条件读取与展示工具。
- [x] 运行 Python 契约测试和网页语法检查。

### Task 2: 修复矩阵与研究工作流

**Files:** `web/js/views/compareMatrix.js`, `web/js/views/projectCheck.js`, `web/js/views/detail.js`, `web/js/views/incubation.js`, `web/js/views/map.js`, `web/js/citation.js`

- [x] 矩阵增加搜索/阻塞点筛选，读取 conditions 并显示缺失态。
- [x] 立项结果增加边界、缺失信息、证据摘要和下一步入口。
- [x] 详情增加条件摘要、证据链、纠错链。
- [x] 孵化清单增加本地验证状态和动作。
- [x] 失败地图分离成功经验并按样本量排序。

### Task 3: 信息架构与视觉高端化

**Files:** `web/js/views/library.js`, `web/css/components.css`, `web/css/base.css`, `web/index.html`

- [x] 经验库增加概览指标和最近证据区。
- [x] 增加证据链、验证状态、矩阵筛选和卡片视觉层级。
- [x] 保持主题一致并修复窄屏布局。

### Task 4: 全量验证与发布

- [x] 运行 `python run_tests.py`、`python tools/check_web.py`、JS 测试。
- [x] 启动 HTTP 服务，实际访问所有视图、矩阵和窄屏。
- [x] 启动公共静态隧道，验证链接可访问。
- [x] 记录最终审查结果和限制。
