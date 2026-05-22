# data 目录说明

你看到的 `data/` 目录就是放原始数据和清洗后面板数据的地方。

## 你可以怎么用

### 方案 A（推荐先跑通）
运行下面命令自动创建 4 个模板 CSV（含表头）：

```bash
python create_data_templates.py
```

会生成：
- `data/wef_infra.csv`
- `data/lpi_infra.csv`
- `data/controls.csv`
- `data/outcomes.csv`

### 方案 B（我帮你继续做）
你把“可公开下载链接”发给我（WEF/LPI/WDI/NTL 的具体链接），我可以继续写下载与整理脚本，自动拉取并合并。

> 注意：有些数据源（特别是 WEF 历史版、LPI 原始文件）可能需要手动登录或人工下载，脚本无法绕过权限。

## 当前脚本行为
- 若 `data/` 下 4 个文件都存在：`construct_transport_index.py` 会读取真实数据。
- 若不存在：会自动使用模拟数据（template mode）跑通流程。
