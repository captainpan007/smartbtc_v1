# SmartBTC_v1 自动交易系统

`SmartBTC_v1` 是一个专注于中长期趋势和震荡交易机会识别的自动化量化交易系统，基于多因子分析、市场状态感知、形态识别、链上数据和情绪指数构建，已支持模拟交易、滑点与手续费评估，并具备实盘扩展能力。

## 📁 项目结构

```
smartbtc_v1/
├── core/
│   ├── signal_generator.py     # 核心信号生成器（融合多因子/形态/情绪/链上数据）
│   ├── strategy_switcher.py    # 策略切换控制器（趋势/震荡切换）
│   ├── executor.py             # 模拟/实盘下单执行模块（含滑点手续费模拟）
│   ├── market_state.py         # 市场状态识别（ADX/布林/波动率/成交量）
├── utils/
│   └── indicators.py           # 技术指标库 + 形态识别函数（Doji、吞没、锤头）
├── config/
│   └── settings.yaml           # 全局配置文件
├── logs/
│   └── trade_log.csv           # 回测/实盘交易记录日志
├── run_backtest.py            # 回测入口脚本
├── run_live.py                # 实盘入口脚本（待扩展）
```

## ✅ 主要功能

- 多因子融合信号生成（形态 + 技术指标 + 链上数据 + 情绪指数）
- 市场状态驱动策略切换
- 策略级止盈止损 + 仓位管理
- 滑点/手续费模拟
- 模块化可替换结构
- 回测与实盘接口统一

## 📦 如何使用

1. 准备历史数据：
    - 默认使用 `core/data/historical/BTCUSDT_4h.csv`
    - 或可通过 `ccxt` 动态下载真实数据

2. 运行回测：
```bash
python run_backtest.py
```

3. 查看日志输出于 `logs/trade_log.csv`

## 📈 下一步规划

- 实盘订单同步接口
- 策略评分器与 Meta Controller
- 多结构胜率分布图与信号可视化面板