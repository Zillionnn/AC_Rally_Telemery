"""UI text catalogue.

Chinese is the source language: `tr()` returns the key unchanged unless the
active language has a translation for it. Wrapping a string that is not in a
catalogue is harmless, it simply stays Chinese.
"""

from __future__ import annotations

LANGUAGES = {"zh": "中文", "en": "English"}

_language = "zh"


def set_language(code: str) -> None:
    global _language
    _language = code if code in LANGUAGES else "zh"


def language() -> str:
    return _language


def tr(text: str) -> str:
    if _language == "zh" or not isinstance(text, str):
        return text
    return EN.get(text, text)


_reversed: dict[str, dict[str, str]] = {}


def _reverse(lang: str) -> dict[str, str]:
    table = _reversed.get(lang)
    if table is None:
        table = {}
        for zh, en in EN.items():
            table[en if lang == "en" else zh] = zh
        _reversed[lang] = table
    return table


def translate_value(text: str, from_lang: str, to_lang: str) -> str:
    """Re-express text that is already showing in `from_lang` as `to_lang`.

    Used to retranslate a live window in place: the widget text is matched
    back to its catalogue key and replaced with the other language.
    """
    if from_lang == to_lang or not isinstance(text, str):
        return text
    key = _reverse(from_lang).get(text)
    if key is None:
        return text
    return key if to_lang == "zh" else EN.get(key, key)


EN = {
    "此 run 没有录像\n自动录像开启后按赛段生成":
        "No video for this run\nOne is made per stage once auto video is on",
    "录像已对齐：视频 {time} = {dist:,.0f} m": "Video aligned: {time} = {dist:,.0f} m",
    "{n} runs · {rate:.0f} Hz · {cur}  /  参考 {ref}":
        "{n} runs · {rate:.0f} Hz · {cur}  /  ref {ref}",
    "● {start:.2f} km   Δ{delta:+.2f}s   入 {ce:.0f}/{re:.0f}  心 {cm:.0f}/{rm:.0f}  出 {cx:.0f}/{rx:.0f}":
        "● {start:.2f} km   Δ{delta:+.2f}s   in {ce:.0f}/{re:.0f}  "
        "apex {cm:.0f}/{rm:.0f}  out {cx:.0f}/{rx:.0f}",
    "路书加载失败：{error}": "Failed to load pacenotes: {error}",
    "已保存 {time} · 分析已更新": "Saved {time} · analysis updated",
    "100m 分段 · 已剔除参考事件 {n} 个（灰色虚线）":
        "100 m splits · {n} reference incidents excluded (grey dashes)",
    "点击缩放到 {start:.0f}–{end:.0f} m\n时间差 {delta:+.3f}s（当前 - 参考）":
        "Click to zoom to {start:.0f}–{end:.0f} m\n"
        "Δ {delta:+.3f}s (current − reference)",
    "点击缩放到 {dist:.0f}m": "Click to zoom to {dist:.0f} m",
    "找不到窗口「{title}」": "Window not found: “{title}”",
    "音频输出失败：{error}": "Audio output failed: {error}",
    "没有可用的 H.264 编码器: {error}": "No usable H.264 encoder: {error}",
    "音频设备不可用: {error}": "Audio device unavailable: {error}",
    "· 游戏数据": "· game data",
    "游戏赛道：{track}": "Game track: {track}",
    "路书表：{table}（{source}）": "Pacenote table: {table} ({source})",
    "自动匹配 · {stage}": "Auto · {stage}",
    "路书距离 {dist:,.0f} m · 赛段相对 {rel:,.0f} m\n参考长度 {length:,.0f} m":
        "Pacenote distance {dist:,.0f} m · stage-relative {rel:,.0f} m\n"
        "Reference length {length:,.0f} m",
    "点击缩放到 {rel:,.0f} m": "Click to zoom to {rel:,.0f} m",
    "{mode} · {stage} · {n} 条": "{mode} · {stage} · {n} notes",
    "{wheel} 温度": "{wheel} temp",
    "{wheel} 胎压": "{wheel} pressure",
    "{time} · {speed:.0f} km/h · {gear}挡 · 油门 {gas:.0f}% · 刹车 {brake:.0f}% · {rows} 行":
        "{time} · {speed:.0f} km/h · gear {gear} · throttle {gas:.0f}% · "
        "brake {brake:.0f}% · {rows} rows",
    "已保存 {time} · 分析更新中…": "Saved {time} · updating analysis…",
    "录像中 · {target}": "Recording · {target}",
    "正在录像 · {target}": "Recording · {target}",
    "录像失败：{error}": "Video failed: {error}",
    "录像 {seconds:.0f}s · {mb:.0f}MB": "Video {seconds:.0f}s · {mb:.0f}MB",
    "录像 {n} · {gb:.2f}GB": "Video {n} · {gb:.2f} GB",
    "录像 {n} · {mb:.0f}MB": "Video {n} · {mb:.0f} MB",
    "{folder}\n共 {n} 段 · {mb:.0f}MB\n点击打开目录":
        "{folder}\n{n} clip(s) · {mb:.0f} MB\nclick to open the folder",
    "已对齐 {dist:,.0f}m ↔ {time}": "Aligned {dist:,.0f} m ↔ {time}",
    "录像已对齐：视频 {time} = ": "Video aligned: {time} = ",
    "{cur}  /  参考 {ref}": "{cur}  /  ref {ref}",
    "Δ 参考  {delta:+.3f}s": "Δ ref  {delta:+.3f}s",
    "参考 · {ref}": "ref · {ref}",
    "点击缩放到 {start:.0f}–{end:.0f} m": "Click to zoom to {start:.0f}–{end:.0f} m",
    "两跑理论最佳  {time}": "Theoretical best  {time}",
    "可提升  +{gain:.2f}s": "Potential gain  +{gain:.2f}s",
    "100m 分段 · 已剔除参考事件 {n} 个":
        "100 m splits · {n} reference incidents excluded",
    "入 {ce:.0f}/{re:.0f}   心 {cm:.0f}/{rm:.0f}   出 {cx:.0f}/{rx:.0f}":
        "in {ce:.0f}/{re:.0f}   apex {cm:.0f}/{rm:.0f}   out {cx:.0f}/{rx:.0f}",
    "画质 {label}": "Quality {label}",
    "录像中…\n回放面板在赛段结束后可播放":
        "Recording…\nThe replay is available once the stage ends",
    "正在扫描 telemetry/*.csv …": "Scanning telemetry/*.csv …",
    "语言 · 立即生效": "Language · applies immediately",
    "语言已切换": "Language switched",
    "语言 · 重启后生效": "Language · takes effect after restart",
    "语言已保存 · 重启客户端后生效": "Language saved · restart the client to apply",
    "拖动调整上方图表高度": "Drag to resize the chart above",
    "正在等待遥测数据…": "Waiting for telemetry…",
    "刷新": "Refresh",
    "重置缩放": "Reset zoom",
    "重置图高": "Reset heights",
    "回放面板": "Replay panel",
    "等待 AC Rally …": "Waiting for AC Rally …",
    "自动录制": "Auto record",
    "自动录像": "Auto video",
    "跑赛段时同步录制画面+系统声音到 telemetry/videos，\n与遥测一一对应；赛段重置的片段会自动删除":
        "Captures the screen and system audio into telemetry/videos while a "
        "stage runs, aligned with the telemetry; aborted stage clips are deleted.",
    "点击打开录像目录": "Click to open the video folder",
    "无录像": "No video",
    "录像窗口": "Capture window",
    "自动匹配会找 AC Rally 窗口；如果游戏窗口名不含这些字，\n从列表里选它。列表按打开面板时刷新。":
        "Auto picks the AC Rally window; if the game window does not contain "
        "those words, choose it from the list (refreshed when the panel opens).",
    "尚无录像\n开启自动录像后按赛段生成":
        "No video yet\nOne is made per stage once auto video is on",
    "尚无录像": "No video yet",
    "回放面板在赛段结束后可播放": "The replay is available once the stage ends",
    "播放": "Play",
    "暂停": "Pause",
    "后退 3 秒": "Back 3 s",
    "前进 3 秒": "Forward 3 s",
    "跟随": "Follow",
    "播放时图表光标和地图跟着视频走": "Charts and map follow the video while playing",
    "静音": "Mute",
    "音量": "Volume",
    "对齐到光标": "Align to cursor",
    "把视频当前位置标成图表光标所在的赛段时刻。\n手动导入的录像用这个对齐一次即可。":
        "Marks the current video position as the stage time of the chart cursor. "
        "Use it once for imported videos.",
    "打开…": "Open…",
    "导入外部录像文件（录屏软件拍的也能用）":
        "Import an external video (screen recordings work too)",
    "录像分辨率与码率（下一段赛段生效）":
        "Capture resolution and bitrate (applies to the next stage)",
    "赛道地图": "Track map",
    "红=比参考慢 绿=更快 · 每100m":
        "Red = slower than reference, green = faster · per 100 m",
    "等待数据…": "Waiting for data…",
    "赛道": "Track",
    "理论最佳  —": "Theoretical best  —",
    "可提升  —": "Potential gain  —",
    "两跑理论最佳  —": "Theoretical best  —",
    "可提升  +": "Potential gain  +",
    "可提升": "Potential gain",
    "100m 分段 · 已剔除参考事件区": "100 m splits · reference incidents excluded",
    "100m 分段 · 已剔除参考事件 ": "100 m splits · reference incidents excluded ",
    "100m 分段 · 同一 run 对比": "100 m splits · current run vs itself",
    "刹车/弯区 · 入 / 弯心 / 出 · 当前 / 参考":
        "Braking/corners · entry / apex / exit · current / reference",
    "自动匹配": "Auto",
    "手动选择": "Manual",
    " · 按距离": " · by distance",
    " · 与本次距离范围不完全匹配": " · not an exact distance match",
    "更慢": "Slower",
    "更快": "Faster",
    "当前": "Current",
    "参考": "Reference",
    "油门 当前": "Throttle current",
    "刹车 当前": "Brake current",
    "油门 参考": "Throttle ref",
    "刹车 参考": "Brake ref",
    "挡位": "Gear",
    "转向 %": "Steering %",
    "横向 G": "Lateral G",
    "纵向 G": "Longitudinal G",
    "ACR Telemetry · 等待 AC Rally": "ACR Telemetry · waiting for AC Rally",
    "显示分析": "Show analysis",
    "打开数据目录": "Open data folder",
    "退出": "Quit",
    "已保存 ": "Saved ",
    "已保存": "Saved",
    " · 分析更新中…": " · updating analysis…",
    " · 分析已更新": " · analysis updated",
    "自动匹配 AC Rally": "Auto (AC Rally)",
    "自动匹配窗口": "Auto window",
    "外部录像 · 需对齐": "External video · align needed",
    "录像就绪": "Video ready",
    "播放失败": "Playback failed",
    "选择录像文件": "Choose a video",
    "视频 (*.mp4 *.mkv *.mov *.avi)": "Video (*.mp4 *.mkv *.mov *.avi)",
    "外部录像已载入 · 把光标放到已知点（如终点）后点“对齐到光标”":
        "External video loaded · move the cursor to a known point (e.g. the "
        "finish) and press “Align to cursor”",
    "加载失败": "Load failed",
    "撞击": "Impact",
    "停车": "Stop",
    "重生": "Respawn",
    "此 run 无赛道数据": "No track data for this run",
    "预览模式 · 自动录制未启动": "Preview mode · auto record is off",
    "距离": "Dist",
    "时间": "Time",
    "速度": "Speed",
    "油门": "Throttle",
    "刹车": "Brake",
    "Δ 参考": "Δ ref",
    "参考速度": "Ref speed",
    "路书": "Pacenotes",
    "没有数据": "No data",
    "需要 velocity 列": "Needs velocity columns",
    "距离 km": "Distance km",
    "平均 km/h": "Avg km/h",
    "最高 km/h": "Max km/h",
    "全油 %": "Full throttle %",
    "刹车 %": "Braking %",
    "滑行 %": "Coasting %",
    "静止 s": "Stationary s",
    "事件": "Events",
    "赛段": "Stage",
    "按路书距离": "by pacenote distance",
    "— 没有可用的赛段路书": "— no stage pacenotes available",
    "— 没有匹配到赛段路书": "— no matching stage pacenotes",
    "距离 (m)": "Distance (m)",
    "已连接共享内存 · 等待赛段": "Shared memory connected · waiting for a stage",
    "已连接 · 进入赛段自动录制": "Connected · records when a stage starts",
    "检测到赛段进行中 · 等待下一次": "Stage already running · waiting for the next one",
    "挡 · 油门 ": " gear · throttle ",
    "% · 刹车 ": "% · brake ",
    "自动录制已开启 · 等待赛段": "Auto record on · waiting for a stage",
    "自动录制已关闭": "Auto record off",
    "自动录像已开启 · 跑赛段时同步录制画面和声音":
        "Auto video on · screen and audio are captured with each stage",
    "自动录像已关闭": "Auto video off",
    "跑完赛段后自动出现在这里 · 点击打开目录":
        "Appears here after a stage · click to open the folder",
    "共 ": "",
    " 段 · ": " clip(s) · ",
    "点击打开目录": "\nclick to open the folder",
    "录像打不开": "Cannot open the video",
    "先加载一段录像再对齐": "Load a video before aligning",
    "已对齐 ": "Aligned ",
    "录像已对齐：视频 ": "Video aligned: ",
    "仍在托盘运行，赛段开始会自动录制":
        "Still running in the tray; recording starts with the next stage",
    "录制已保存，但数据不足 5 秒，未加入分析":
        "Saved, but under 5 s of data so it was not added to the analysis",
    "telemetry/ 下没有可用 CSV": "No usable CSV under telemetry/",
    "  /  参考 ": "  /  ref ",
    "Δ 参考  0.000s": "Δ ref  0.000s",
    "参考 · ": "ref · ",
    "终点": "Finish",
    "点击缩放到 ": "Click to zoom to ",
    "— 暂无可分析的干净分段": "— no clean segment to analyse yet",
    "可提升 · 当前更慢": "Gains · current is slower",
    "已获得 · 当前更快": "Gains · current is faster",
    "— 没有检测到刹车区": "— no braking zones detected",
    "s   入 ": "s   in ",
    "   心 ": "  apex ",
    "   出 ": "  out ",
    "  · 参考事件附近": "  · near a reference incident",
    "CLEAN · 无停车 / 撞击 / 重生": "CLEAN · no stop / impact / respawn",
    "客户端已经在运行，请从系统托盘打开。":
        "The client is already running; open it from the system tray.",
    "画质 ": "Quality ",
    "游戏赛道：": "Game track: ",
    "路书表：": "Pacenote table: ",
    "路书加载失败：": "Failed to load pacenotes: ",
    "自动匹配 · ": "auto · ",
    " 温度": " temp",
    " 胎压": " pressure",
    "录像中 · ": "Recording · ",
    "录像中…": "Recording…",
    "正在录像 · ": "Recording · ",
    "录像失败：": "Video failed: ",
    "录像失败": "Video failed",
    "录像 ": "Video ",
    "此 run 没有录像": "No video for this run",
    "时间差 ": "Δ ",
    "赛段重置 · 录像已丢弃": "Stage reset · video discarded",
    "赛段重置 · 等待下一次": "Stage reset · waiting for the next one",
    "路书距离 ": "Pacenote distance ",
    " m · 赛段相对 ": " m · stage-relative ",
    "参考长度 ": "Reference length ",
    "与下一条连贯": "continues into the next note",
    "遥测照常录制": "Telemetry keeps recording",
    "录像中断": "Video interrupted",
    "录制中": "Recording",
    "录像启动失败": "Video failed to start",
    "找不到窗口「": "Window not found: “",
    "等待下一次赛段": "Waiting for the next stage",
    "打不开这个录像文件": "Cannot open this video file",
    "录像里没有画面": "The video has no picture",
    "音频输出失败：": "Audio output failed: ",
    "找不到游戏窗口": "Game window not found",
    "没有可用的 H.264 编码器: ": "No usable H.264 encoder: ",
    "音频设备不可用: ": "Audio device unavailable: ",
    "转换失败 x%d: %s": "Conversion failed x%d: %s",
}
