## Usage

```bash
mv cfg.example.json cfg.json
pip install -r requirement.txt
./contorl start
```

## Config
```
{
  "step": 60,
  "ping_count": 5,  #每个host执行fping的次数
  "debug": true,
  "transfers": [
    "192.168.6.222:6060"
  ],
  "http": 2224,
  "DC": "HL",
  "targets": {
    "alive-ping-test": "192.168.6.222"
  }
}
```

## Metrics
```
{
    "alive.ping.alive":"采集器状态（1存活，0不存活）",
    "alive.ping.status":"存活状态（1存活，0不存活）",
    "alive.ping.avg":"平均响应时间",
    "alive.ping.loss_rate":"丢包率",
}
```
