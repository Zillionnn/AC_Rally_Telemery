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
- **界面语言**：中文 / English 可切换（右上角下拉，立即生效并记住；`--lang en` 可直接以英文启动）。

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
.build_venv/Scripts/pip install numpy==2.2.6 PySide6 pyqtgraph nuitka zstandard windows-capture av PyAudioWPatch opencv-python
.build_venv/Scripts/python acr_desktop.py --telemetry-dir dist/telemetry
```

`dist/telemetry` 不存在也能启动（界面显示暂无数据，开始录制后会自动创建）。

## 打包

依赖见上一节（Nuitka 已在依赖列表里）。Windows 上 Nuitka 走 MSVC：需要 Visual Studio Build Tools 2019/2022（勾选“使用 C++ 的桌面开发”）。

**以下命令都在仓库根目录执行**（`acr_build.py`、`acr_installer.iss` 都在根目录，不要在 `dist\` 里执行）：

```bash
cd /d D:\path\to\ACRallyRec
```

### 单文件 exe

```bash
.build_venv/Scripts/python acr_build.py check      # standalone 构建，并校验 Qt 插件等 6 个必需文件
.build_venv/Scripts/python acr_build.py onefile    # 单文件 exe → build_exe/ACR Telemetry.exe
```

然后把 exe 部署到 `dist\`（安装包从这里取文件）：

```bash
if not exist "dist" mkdir "dist"
copy /y "build_exe\ACR Telemetry.exe" "dist\ACR Telemetry.exe"
```

### 安装包（可选）

本机直接从 `dist\` 运行不需要安装包；这一节只用于**分发给别人**或想要固定安装目录/卸载项的场景。注意安装版的数据目录是**安装目录下的 `telemetry\`**，与 `dist\telemetry` 不是同一份，需要旧数据时复制过去。

需要 [Inno Setup 6+](https://jrsoftware.org/isinfo.php)（**只需安装一次**，默认安装即可；`ISCC.exe` 默认不在 PATH 里，用完整路径或自己加 PATH）：

| 版本 | ISCC 默认位置 |
|---|---|
| Inno Setup 7（x64） | `C:\Program Files\Inno Setup 7\ISCC.exe` |
| Inno Setup 6 | `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` |

版本号与 `acr_version.py` 保持一致（当前 0.3.16）：

```bash
"C:\Program Files\Inno Setup 7\ISCC.exe" /DMyAppVersion=0.3.16 acr_installer.iss
```

产物：`dist\ACR Telemetry Setup 0.3.16.exe`，中文/English 安装向导（中文翻译在 `installer\ChineseSimplified.isl`，
按系统语言自动选择）。安装包按用户装到 `%LOCALAPPDATA%\Programs\ACR Telemetry`
（不需要管理员权限），创建开始菜单和桌面快捷方式，并在安装目录下建 `telemetry\` 作为数据目录；
卸载走“设置 → 应用”或安装目录里的 `unins000.exe`，升级时直接运行新安装包覆盖安装即可。
旧数据把原来的 `telemetry\` 目录复制进安装目录就能继续用。

## 运行

打包后直接双击 `dist\ACR Telemetry.exe` 即可（单文件，不需要安装）。数据目录是 **exe 同目录下的 `telemetry\`**，例如 `dist\telemetry\`。

- 关闭窗口是**隐藏到托盘**（托盘模式），不是退出；重新打开点任务栏右下角 `^` 里的 ACR Telemetry 图标，退出用托盘图标右键 → 退出。
- 双击时若弹“客户端已经在运行，请从系统托盘打开”：说明已有一个实例在托盘里（单实例锁），从托盘打开即可；找不到托盘图标就结束任务管理器里的 `ACR Telemetry.exe`，或删除 exe 同目录的 `acr_telemetry.lock` 后重开。

## 常见问题

### 双击时提示“打开文件 - 安全警告 / 无法验证发布者”

现象：每次双击 `ACR Telemetry.exe` 都弹“无法验证发布者。你确定要运行此软件吗？”，点“运行”后也可能没有反应。

原因：文件被 Windows 打上了“来自 Internet”标记（NTFS 备用数据流 `Zone.Identifier`，浏览器、聊天工具下载或从压缩包转存时产生），**与程序本身无关，本地构建产物没有这个标记**。排查：

```powershell
Get-Item '.\ACR Telemetry.exe' -Stream *          # 看是否存在 Zone.Identifier
Get-Content '.\ACR Telemetry.exe' -Stream Zone.Identifier   # 通常显示 ZoneId=3
```

解决（任一）：

- 右键文件 → 属性 → 常规 → 勾选“解除锁定” → 应用；
- PowerShell：`Unblock-File '.\ACR Telemetry.exe'`；
- 改用安装包安装（安装包内的文件不带该标记）。

注意：NTFS 内复制文件会连这个数据流一起复制（所以“复制到 %TEMP%”不一定能去掉它）；不要把浏览器/聊天工具里收到的 exe 直接覆盖到 `dist\`，用 `acr_build.py onefile` 的产物。

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
acr_version.py   版本号（exe 文件版本与安装包默认版本）
acr_installer.iss Inno Setup 安装包脚本
installer/       安装包中文翻译（ChineseSimplified.isl）
pacenotes/       从游戏资源抽取的路书数据
```

## 分支

`master` 是 Python 实现（上述客户端）。`rust` 分支是一份并行的 Rust/egui 重写，不在本仓库发布。

## 署名

本项目由作者与 **DeepSeek Harness** 的 AI 编程代理（模型 `deepseek-flash`）协作完成：客户端界面、图表与回放面板的实现、问题定位、验证与打包均有该代理参与。

## 许可

MIT，见 [LICENSE](LICENSE)。仅用于离线分析与个人训练，不包含任何游戏文件。
