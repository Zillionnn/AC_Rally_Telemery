# Context

## 术语

- **Client（客户端）**：用户日常打开的桌面程序；负责连接共享内存、自动录制、展示分析。不使用 .bat 启动。
- **Stage（赛段）**：AC Rally 的一次计时赛段；以游戏内赛段计时 `current_time` 为唯一计时依据，是自动录制的单位。
- **Run（跑次）**：一次 Stage 录制产生的数据文件及其分析结果。
- **Reference Run（参考跑次）**：用于对比的另一个 Run；默认取除当前 Run 外最快的一次。
- **Auto-record（自动录制）**：Client 在 Stage 计时开始后自动写 CSV、在 Stage 结束后自动保存并刷新分析。
- **Armed（待录）**：已连接共享内存、当前不录制，等待下一次 Stage 计时从 0 开始。
- **Waiting for Next（等下一跑）**：Client 启动时 Stage 已在跑，当前这次不录，等下一次 Stage。
- **Completed Stage（完成赛段）**：计时到达终点并正常结束的 Stage；只有它成为 Run。
- **Aborted Run（中止跑次）**：中途重置赛段产生的未完成录制；按用户选择丢弃，不进入分析。客户端异常退出/崩溃时保留碎片用于恢复。
- **Client Package（客户端交付）**：单文件 exe；exe 同目录的 `telemetry/` 为数据目录；不使用 .bat。
- **Tray Mode（托盘模式）**：手动启动；关闭窗口隐藏到托盘；自动录制常驻；不开机自启。
- **Tray Notification（托盘通知）**：赛段保存后右下角提示，不抢焦点。
- **Retention（保留策略）**：保留全部 Run，不自动删除。
- **Incident（事件）**：录制数据中检测到的重生、停车或撞击；参考 Run 的事件不参与“可提升时间”的分段理论最佳计算。
- **Theoretical Best（理论最佳）**：当前 Run 与 Reference Run 在干净分段上取更快分段累加得到的参考成绩。
- **Potential Gain（可提升）**：当前 Run 成绩与 Theoretical Best 的差。
- **Pace Note（路书）**：游戏 `DT_Pacenote*` 表里的真实领航提示；按赛段样条距离标注，不由遥测生成。
- **Pacenote Table（路书表）**：一个赛段方向/分段对应的路书数据；与遥测的绝对 `distance_traveled` 对齐。
- **Stage Match（赛段匹配）**：为当前 Run 选择路书表；优先用录制 meta 的 track/config，缺失时按距离范围自动匹配，允许手动覆盖。
- **Track Label（赛道显示）**：主界面“赛道”行显示的名称；有游戏 static meta 时优先显示真实赛道，否则显示按距离推断的路书表并标注“按路书距离”。
- **Inferred Stage（推断赛段）**：没有 meta track/config 的旧 Run，只能按起止距离匹配到的路书表；界面必须标注这是推断而不是游戏数据。
- **Track Map（赛道地图）**：由遥测重建的 2D 行驶轨迹；横向坐标用 `velocity_z` 按墙钟积分补全，用于定位慢点，不等同于游戏赛道样条。
- **Replay Panel（回放面板）**：客户端右侧的视频 + 赛道地图区域，可与图表同时显示。
- **Auto Video（自动录像）**：客户端在赛段开始时自动录实时驾驶画面、结束时自动停录；与遥测共用 Auto-record 状态机，默认开启，可单独关闭。
- **Video Recorder（录像器）**：客户端内置的屏幕+声音录制器；Windows Graphics Capture 捕获游戏窗口，WASAPI loopback 捕获系统输出，编码为 MP4（H.264 + AAC），不依赖 OBS/Game Bar。
- **Replay Video（回放视频）**：Auto Video 产生的带声音实时驾驶视频；也允许手动加载外部视频用于旧 Run。客户端只保存路径和偏移，不复制/剪辑。
- **Audio Track（音轨）**：录像器从默认扬声器 loopback 采集的系统输出，48kHz 立体声、AAC；会包含游戏声以及其他正在播放的应用声音；界面提供静音/音量。
- **Video Offset（视频偏移）**：`video_time = stage_time + offset`；自动录像根据首帧赛段时刻自动计算，可 ±0.1s 微调；外部视频用任意已知点一键对齐。
- **Alignment Point（对齐点）**：手动对齐外部视频时使用的起点或明显弯道。
- **Video Folder（视频目录）**：`telemetry/videos/`；默认保留全部视频，界面显示总占用，并提供打开目录/手动清理。
- **Map Cursor（地图光标）**：与图表光标、视频帧同步的赛道位置圆点；点击地图可反向定位图表和视频。
- **Chart Height（图高）**：每个图表单独设置的像素高度；拖动某个图的下边缘只改变该图高度，其他图不变，图表区总高度随之增减。
- **Chart Handle（图高拖柄）**：每个图表底部的可拖动分隔柄；用于调整其上方图表的高度。
- **Chart Scroll（图表滚动）**：图表区的垂直滚动；总高度超出窗口时可用滚轮上下查看，Ctrl+滚轮用于横向缩放。
- **Chart Layout Preset（默认图高）**：按当前窗口高度分配的 6 图默认高度比例；可一键恢复，并跨重启保存用户自定义高度。
