# ACR Telemetry Studio

Assetto Corsa Rally（UE5）的遥测分析与回放桌面客户端：赛段跑完自动落盘、自动分析，并能把"哪里慢"落到图表和赛道地图上。

![界面](assets/acr.png)

## 功能

- **自动录制**：读取游戏共享内存（`Local\acpmf_physics/graphics/static`，约 333Hz），赛段计时开始即录，结束自动保存并刷新分析；托盘常驻，不抢焦点。
- **赛段分析**：分段 delta、1km splits、刹车区、事故（停车/撞击/重生）、两跑理论最佳、可提升时间；内置游戏真实的 44 张路书（Pace Notes）。
- **六图联动**：DELTA / SPEED / THROTTLE-BRAKE / GEAR-RPM / STEERING-G / TYRES，可逐图调高度；拖动或 Ctrl+滚轮缩放，缩放后拖动不再掉帧。
- **赛道地图**：由世界系速度积分重建（`∫vx`、`−∫vz`，纵向恒定比例，缩小裁切不压扁），按每 100m 局部 delta 着色，可点击定位。
- **内置录像**：Windows Graphics Capture + WASAPI 环回 + NVENC 硬件编码（1080p60，约 1MB/s），与遥测同时间轴，回放时光标/地图跟随。
- **加载缓存**：按文件签名缓存每个 run 的解析结果，20 个 run、1.3GB CSV 冷启动约 50s，之后热启动 0.5s 级，新赛段只解析新增文件。
- **界面语言**：中文 / English 可切换（右上角下拉，保存后重启生效；`--lang en` 可直接以英文启动）。

## 数据来源

游戏只提供共享内存，不修改游戏本身。录制结果为 `telemetry/` 下的：

```
acr_telemetry_YYYYMMDD_HHMMSS.csv   遥测原始帧（约 333Hz）
acr_telemetry_YYYYMMDD_HHMMSS.meta.json  赛道/车辆/赛段长度/视频信息
videos/*.mp4                        内置录像（可选）
.acr_cache/                         解析缓存，可随时删除（只会慢一次）
ui_layout.json                      窗口与图高布局
```

## 从源码运行

需要 **CPython 3.12**（Nuitka 打包要求，Anaconda 的 numpy 会让产物启动失败）：

```bash
python -m venv .build_venv
.build_venv/Scripts/pip install numpy==2.2.6 PySide6 pyqtgraph nuitka zstandard windows-capture av PyAudioWPatch
.build_venv/Scripts/python acr_desktop.py --telemetry-dir dist/telemetry
```

## 打包

```bash
.build_venv/Scripts/python acr_build.py check      # standalone，并校验 Qt 插件等 6 个必需文件
.build_venv/Scripts/python acr_build.py onefile    # 单文件 exe → build_exe/ACR Telemetry.exe
```

Nuitka 的 `--enable-plugin=pyside6` 与 QtOpenGL/QtSvg 的 include 已固化在脚本里；不要删除输出目录，缓存能让后续构建只重编改动的模块。

## 自检

```bash
"ACR Telemetry.exe" --screenshot out.png --current 0 --telemetry-dir dist/telemetry
"ACR Telemetry.exe" --screenshot out.png --lang en                 # 英文界面
"ACR Telemetry.exe" --record-test 3 --record-window "Assetto Corsa Rally"   # 验证窗口捕获+编码+音频
```

## 目录

```
acr_desktop.py   界面、图表、地图、回放面板
acr_data.py      CSV 解析、run 组装、分析、缓存
acr_track.py     路径重建与 delta 着色
acr_pacenotes.py 游戏路书
acr_live.py      共享内存录制状态机
acr_video.py     屏幕+系统音频录制
acr_play.py      回放解码与音频输出
acr_build.py     Nuitka 构建脚本
pacenotes/       从游戏资源抽取的路书数据
```

## 分支

`master` 是 Python 实现（上述客户端）。`rust` 分支是一份并行的 Rust/egui 重写，不在本仓库发布。

## 许可

MIT，见 [LICENSE](LICENSE)。仅用于离线分析与个人训练，不包含任何游戏文件。
