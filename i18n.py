"""English and Chinese for every string the board puts on screen.

Two rules hold this together:

1. Nothing in the app builds a user-visible sentence by concatenation. A string
   is a key plus parameters, so a translation can put the parts in a different
   order, which Chinese frequently needs.

2. The board's cells are TOKENS, not labels. The grid stores "THANK YOU"
   forever; what the person reads is `cell("THANK YOU")`, and what gets spoken
   is that same label. A caregiver's own phrase has no translation, so it falls
   back to exactly what they typed — which is the right answer, since they
   typed it in the language they speak.
"""

LANGUAGES = ("en", "zh")

_current = "en"
_bound = []


STRINGS = {
    "en": {
        # ── window / chrome ───────────────────────────────────────────────
        "app.title": "EMOTIV BCI Assistive Communication System",
        "nav.language": "Language",
        "nav.phrases": "📝 Phrases",
        "nav.api_settings": "⚙️ API Settings",
        "nav.contact_quality": "Contact Quality",
        "nav.eeg_quality": "EEG Quality",
        "nav.back": "‹ Back",

        # ── headset list ──────────────────────────────────────────────────
        # ── approval in EMOTIV Launcher ───────────────────────────────────
        "access.credentials_title": "Your EMOTIV application keys are needed",
        "access.credentials_body": "The board talks to Cortex as an application, and "
                                   "every person uses their own free key. Create one at "
                                   "emotiv.com → My Account → Cortex Apps, then paste "
                                   "the Client ID and Client Secret here. They are "
                                   "stored on this computer only.",
        "access.enter_credentials": "Enter keys",
        "access.pending_title": "Approve this app in EMOTIV Launcher",
        "access.pending_body": "EMOTIV Launcher is asking whether this application may "
                               "use your headset. Switch to the Launcher, approve it, "
                               "and this screen carries on by itself. It is checking "
                               "every few seconds.",
        "access.check_again": "Check now",
        "access.rejected_title": "Access was declined",
        "access.rejected_body": "EMOTIV Launcher declined this application. Approve it "
                                "there, or ask again below.",
        "access.ask_again": "Ask again",
        "access.failed_title": "Cortex refused these keys",
        "access.failed_body": "Cortex did not accept this Client ID and Client Secret: "
                              "{detail}",
        "status.awaiting_approval": "Waiting for approval in EMOTIV Launcher…",
        "status.access_granted": "Approved. Connecting…",
        "status.access_rejected": "EMOTIV Launcher declined this application.",

        "device.title": "Choose a headset",
        "device.subtitle": "Every headset the EMOTIV Launcher can see. Pick the one "
                           "on the person's head.",
        "device.searching": "Searching for headsets…",
        "device.none_title": "No headset found",
        "device.none_body": "Turn the headset on, and make sure the EMOTIV Launcher is "
                            "running and signed in. The dongle should be plugged in, or "
                            "the headset paired over Bluetooth.",
        "device.refresh": "Search again",
        "device.connect": "Connect",
        "device.connecting": "Connecting to {headset}…",
        "device.status.connected": "Connected",
        "device.status.discovered": "Found, not connected",
        "device.status.connecting": "Connecting…",
        "device.status.unknown": "Unknown state",
        "device.by.dongle": "USB dongle",
        "device.by.bluetooth": "Bluetooth",
        "device.by.usb": "USB cable",
        "device.channels": "{count} channels: {names}",
        "device.facial_yes": "Mental commands + facial expressions",
        "device.facial_no": "Mental commands only — this headset has no facial "
                            "expression stream",
        "device.unknown_model": "Unrecognised model — sensors will be read from the "
                                "headset itself",

        # ── pre-flight ────────────────────────────────────────────────────
        "setup.device_connecting": "DEVICE: CONNECTING…",
        "setup.device": "DEVICE: {headset}",
        "setup.cq_title": "How to ensure good Contact Quality?",
        # One per headset family: the sensors are not the same shape, are not in
        # the same place, and are not adjusted the same way.
        "setup.cq_body": "Work each sensor onto the skin until it turns green. Start "
                         "with the reference sensors if the headset has them — nothing "
                         "else can read well until those do.",
        "setup.cq_body.insight": "Work each sensor underneath hair to make contact with "
                                 "the scalp. If all sensors are black, first adjust the "
                                 "reference sensors (the two pointy cones on the arm "
                                 "behind the left ear) until they are green, and then "
                                 "adjust the other sensors.",
        "setup.cq_body.epoc": "Wet every felt pad with saline until it is damp but not "
                              "dripping, then press each arm so the pad reaches the "
                              "scalp through the hair. The two reference sensors behind "
                              "the ears have to be green before any other sensor can be.",
        "setup.cq_body.mn8": "MN8's two sensors are in the earpieces. Seat each one "
                             "firmly in the ear, and give it a few seconds to settle — "
                             "the reading climbs as the contact warms up.",
        "setup.eq_title": "How to ensure stable EEG Quality?",
        "setup.eq_body": "EEG Quality tracks electrical noise and data saturation. Keep "
                         "the facial muscles relaxed, avoid jaw clenching, and limit "
                         "sudden movements.\n\n"
                         "• Black nodes mean heavy noise or a saturated sensor.\n"
                         "• Orange nodes mean moderate interference.\n"
                         "• Green nodes mean clean signal is arriving.",
        "setup.continue": "Continue ›",
        "setup.ready": "Every sensor is good. You can start.",
        "setup.waiting_one": "One more sensor to adjust.",
        "setup.waiting_many": "{count} more sensors to adjust.",
        "setup.continue_anyway": "You can continue anyway — a sensor that is not green "
                                 "simply contributes nothing.",
        "setup.no_data": "No readings yet. Check the headset is switched on and the "
                         "EMOTIV Launcher is signed in. You can still continue.",
        "setup.two_channel_note": "This headset has only these two sensors, so there "
                                  "is no head map to fill in. Both have to be green "
                                  "before the board will accept a selection.",

        # ── board ─────────────────────────────────────────────────────────
        "board.composed": "Composed Message: {text}",
        "board.speak": "🔊 SPEAK",
        "board.backspace": "⌫ BACKSPACE",
        "board.pause": "⏸️ PAUSE",
        "board.resume": "▶️ RESUME",
        "board.exit": "✕ EXIT APP",
        "board.mode": "Mode: AUTOMATIC SCAN",
        "board.speed": "Speed:",
        "board.include_mental": "Include Mental Commands",
        "board.include_facial": "Include Facial Expressions",
        "board.facial_unsupported": "Facial expressions are not available on this headset",
        "board.mental_sens": "Mental Cmd Sens: {value}",
        "board.facial_sens": "Facial Sens: {value}",
        "board.cooldown": "Cooldown: {value}s",
        "speed.very_slow": "VERY SLOW",
        "speed.slow": "SLOW",
        "speed.medium": "MEDIUM",
        "speed.fast": "FAST",
        "speed.very_fast": "VERY FAST",

        # ── what triggers what ────────────────────────────────────────────
        "controls.both": "{select_thought}/{select_facial} = SELECT  •  "
                         "{speed_thought}/{speed_facial} = SPEED",
        "controls.mental": "{select_thought} = SELECT  •  {speed_thought} = SPEED",
        "controls.facial": "{select_facial} = SELECT  •  {speed_facial} = SPEED",
        "controls.none": "ALL BCI OVERRIDES DISABLED",

        # ── the live state banner ─────────────────────────────────────────
        "telemetry.line": "BCI FRAMEWORK — MENTAL COMMAND INTENT: {mental}   |   "
                          "FACIAL EMG STATE: {facial}",
        "telemetry.disabled": "DISABLED",
        "telemetry.unsupported": "NOT ON THIS HEADSET",
        "telemetry.neutral": "NEUTRAL (IDLING) [Power: {power}]",
        "telemetry.facial_ready": "READY (IDLING)",
        "telemetry.paused": "SCANNER PAUSED",
        "telemetry.below": "{command} ({action}) [Power: {power}] (Below Threshold)",
        "telemetry.locked": "{command} ({action}) [Power: {power}] (LOCKED)",
        "telemetry.holding": "HOLDING {command} ({action})… ({elapsed}s / {needed}s)",
        "telemetry.triggered": "TRIGGERED {command}! [Power: {power}]",
        "telemetry.triggered_facial": "TRIGGERED {command} ({action} BACKUP)! [Power: {power}]",
        "telemetry.cooldown": "⏳ BCI PAUSE — [{phase}]  |  RESUMING IN {seconds}s  "
                              "(RELAX MIND / FACE)",
        "action.select": "SELECT",
        "action.speed": "CHANGE SPEED",
        "action.speed_short": "SPEED",
        "phase.row_locked": "ROW LOCKED",
        "phase.selection_complete": "SELECTION COMPLETE",
        "phase.cancelled": "ROW CANCELLED",

        # ── quality pill, live on the board screen ────────────────────────
        "pill.contact": "Contact {percent}%",
        "pill.eeg": "EEG {percent}%",
        "pill.battery": "🔋 {percent}%",
        "pill.no_data": "—",
        "pill.warning": "⚠ Signal dropped on {names} — check the sensor(s)",

        # ── status line ───────────────────────────────────────────────────
        "status.waiting": "Waiting for connection payload sequence…",
        "status.connecting": "Connecting to Cortex Service…",
        "status.linked": "Cortex linked. Waiting for device packets…",
        "status.live": "Live stream active. Monitoring diagnostics…",
        "status.loading_profile": "Loading profile: {profile}…",
        "status.failed": "Cortex connection failed: {detail}",
        "status.no_cortex_file": "Could not find the cortex.py file.",
        "status.config_error": "Error loading config.json: {detail}",
        "status.scanner_active": "Scanner active.",
        "status.scanner_paused": "Scanner PAUSED.",
        "status.cooldown": "Cooldown active ({seconds}s)…",
        "status.stream_refused": "{stream} was refused by Cortex: {detail}",

        # ── board cells ───────────────────────────────────────────────────
        "cell.YES": "YES",
        "cell.NO": "NO",
        "cell.MAYBE": "MAYBE",
        "cell.I DON'T KNOW": "I DON'T KNOW",
        "cell.THANK YOU": "THANK YOU",
        "cell.SOMETHING ELSE": "SOMETHING ELSE",
        "cell.BACKSPACE": "BACKSPACE",
        "cell.SPEAK": "SPEAK",
        "cell.SPACE": "SPACE",
        "cell.PAUSE SCANNER": "PAUSE SCANNER",
        "cell.CLEAR MESSAGE": "CLEAR MESSAGE",
        "cell.FLIP OVER": "FLIP OVER",
        "cell.CANCEL": "CANCEL",
        "cell.I HAVE TO TELL YOU SOMETHING": "I HAVE TO TELL YOU SOMETHING",
        "cell.I LOVE YOU": "I LOVE YOU",
        "cell.YOU'RE WELCOME": "YOU'RE WELCOME",
        "cell.HELLO": "HELLO",
        "cell.I AM": "I AM",
        "cell.HAPPY": "HAPPY",
        "cell.SAD": "SAD",
        "cell.TIRED": "TIRED",
        "cell.HOT": "HOT",
        "cell.COLD": "COLD",
        "cell.EXCITED": "EXCITED",
        "cell.I HAVE A PROBLEM": "I HAVE A PROBLEM",
        "cell.PAIN": "PAIN",
        "cell.CRAMP": "CRAMP",
        "cell.ITCH": "ITCH",
        "cell.STOP": "STOP",
        "cell.SICK": "SICK",
        "cell.UNCOMFORTABLE": "UNCOMFORTABLE",
        "cell.I NEED": "I NEED",
        "cell.SUCTION": "SUCTION",
        "cell.MEDICINE": "MEDICINE",
        "cell.BATHE": "BATHE",
        "cell.BATHROOM": "BATHROOM",
        "cell.BED": "BED",
        "cell.BREATHING MACHINE": "BREATHING MACHINE",
        "cell.MASSAGE": "MASSAGE",
        "cell.LEG": "LEG",
        "cell.ARM": "ARM",
        "cell.HIPS": "HIPS",
        "cell.HEAD": "HEAD",
        "cell.LEFT": "LEFT",
        "cell.RIGHT": "RIGHT",
        "cell.I WANT": "I WANT",
        "cell.FOOD": "FOOD",
        "cell.DRINK": "DRINK",
        "cell.TV": "TV",
        "cell.PHONE": "PHONE",
        "cell.COMPUTER": "COMPUTER",
        "cell.HELP": "HELP",
        "cell.TO GO": "TO GO",
        "cell.TO CALL": "TO CALL",
        "cell.A HUG": "A HUG",
        "cell.A KISS": "A KISS",
        "cell.COMPANY": "COMPANY",
        "cell.WAIT": "WAIT",
        "cell.PLEASE GUESS": "PLEASE GUESS",

        # ── dialogs ───────────────────────────────────────────────────────
        "phrases.title": "Caregiver Custom Phrase Manager",
        "phrases.header": "📝 Manage Communication Board Phrases",
        "phrases.subtitle": "Caregivers can add daily requests, family names, or custom "
                            "phrases below.",
        "phrases.add": "Add phrase",
        "phrases.remove": "Remove selected",
        "phrases.reset": "Restore defaults",
        "phrases.save": "Save",
        "phrases.cancel": "Cancel",
        "phrases.prompt_title": "New phrase",
        "phrases.prompt_body": "Phrase to add to the board:",
        "creds.title": "EMOTIV Cortex credentials",
        "creds.client_id": "Client ID",
        "creds.client_secret": "Client Secret",
        "creds.profile": "Profile name",
        "creds.select_thought": "SELECT — mental command",
        "creds.select_facial": "SELECT — facial expression",
        "creds.speed_thought": "CHANGE SPEED — mental command",
        "creds.speed_facial": "CHANGE SPEED — facial expression",
        "creds.include_mental": "Include mental commands",
        "creds.include_facial": "Include facial expressions",
        "creds.save": "Save",
        "creds.cancel": "Cancel",
        "creds.help": "Create an application at emotiv.com → My Account → Cortex Apps, "
                      "then paste its Client ID and Client Secret here. The profile is "
                      "the trained EMOTIV BCI profile to load.",
    },

    "zh": {
        "app.title": "EMOTIV 脑机接口辅助沟通系统",
        "nav.language": "语言",
        "nav.phrases": "📝 短语",
        "nav.api_settings": "⚙️ API 设置",
        "nav.contact_quality": "接触质量",
        "nav.eeg_quality": "脑电质量",
        "nav.back": "‹ 返回",

        "access.credentials_title": "需要你的 EMOTIV 应用密钥",
        "access.credentials_body": "沟通板以“应用”的身份连接 Cortex，每个人都使用自己的免费密钥。"
                                   "请在 emotiv.com → My Account → Cortex Apps 创建一个应用，"
                                   "然后把 Client ID 和 Client Secret 填到这里。"
                                   "它们只保存在这台电脑上。",
        "access.enter_credentials": "填写密钥",
        "access.pending_title": "请在 EMOTIV Launcher 中批准本应用",
        "access.pending_body": "EMOTIV Launcher 正在询问是否允许本应用使用你的头戴设备。"
                               "请切换到 Launcher 并点击批准，本页面会自动继续，"
                               "它每隔几秒就会检查一次。",
        "access.check_again": "立即检查",
        "access.rejected_title": "访问被拒绝",
        "access.rejected_body": "EMOTIV Launcher 拒绝了本应用。请在 Launcher 中批准，"
                                "或在下方重新申请。",
        "access.ask_again": "重新申请",
        "access.failed_title": "Cortex 不接受这组密钥",
        "access.failed_body": "Cortex 拒绝了该 Client ID 与 Client Secret：{detail}",
        "status.awaiting_approval": "正在等待 EMOTIV Launcher 中的批准…",
        "status.access_granted": "已批准，正在连接…",
        "status.access_rejected": "EMOTIV Launcher 拒绝了本应用。",

        "device.title": "选择头戴设备",
        "device.subtitle": "以下是 EMOTIV Launcher 能看到的全部设备，请选择使用者正在佩戴的那一台。",
        "device.searching": "正在搜索设备…",
        "device.none_title": "未找到设备",
        "device.none_body": "请打开头戴设备，并确认 EMOTIV Launcher 已运行并已登录。"
                            "同时请插好 USB 接收器，或确认设备已通过蓝牙配对。",
        "device.refresh": "重新搜索",
        "device.connect": "连接",
        "device.connecting": "正在连接 {headset}…",
        "device.status.connected": "已连接",
        "device.status.discovered": "已找到，未连接",
        "device.status.connecting": "正在连接…",
        "device.status.unknown": "状态未知",
        "device.by.dongle": "USB 接收器",
        "device.by.bluetooth": "蓝牙",
        "device.by.usb": "USB 数据线",
        "device.channels": "{count} 个电极：{names}",
        "device.facial_yes": "意念指令 + 面部表情",
        "device.facial_no": "仅支持意念指令 —— 该设备没有面部表情数据流",
        "device.unknown_model": "未识别的型号 —— 电极信息将直接从设备读取",

        "setup.device_connecting": "设备：正在连接…",
        "setup.device": "设备：{headset}",
        "setup.cq_title": "如何获得良好的接触质量？",
        "setup.cq_body": "请调整每个电极，直到它变绿。如果该设备有参考电极，请先调整参考电极 —— "
                         "在它们就绪之前，其他电极都读不准。",
        "setup.cq_body.insight": "请把每个电极拨到头发下面，让它直接接触头皮。"
                                 "如果所有电极都是黑色，请先调整参考电极"
                                 "（左耳后支架上的两个尖头电极），等它们变绿之后再调整其他电极。",
        "setup.cq_body.epoc": "请用生理盐水把每块绒垫润湿（湿润即可，不要滴水），"
                              "然后压下每个支架，让绒垫穿过头发接触头皮。"
                              "耳后的两个参考电极必须先变绿，其他电极才会准确。",
        "setup.cq_body.mn8": "MN8 的两个电极在耳塞上。请把耳塞稳稳地戴进耳朵，"
                             "并等待几秒钟 —— 接触稳定之后读数会慢慢上升。",
        "setup.eq_title": "如何获得稳定的脑电质量？",
        "setup.eq_body": "脑电质量反映的是电噪声和信号饱和程度。请放松面部肌肉，"
                         "不要咬紧牙关，并尽量减少突然的动作。\n\n"
                         "• 黑色表示噪声很大或电极已饱和。\n"
                         "• 橙色表示存在中等程度的干扰。\n"
                         "• 绿色表示收到的是干净的信号。",
        "setup.continue": "继续 ›",
        "setup.ready": "所有电极状态良好，可以开始了。",
        "setup.waiting_one": "还有 1 个电极未就绪。",
        "setup.waiting_many": "还有 {count} 个电极未就绪。",
        "setup.continue_anyway": "也可以直接继续 —— 未变绿的电极只是不参与读取。",
        "setup.no_data": "尚未收到数据。请确认头戴设备已开机，并且 EMOTIV Launcher 已登录。"
                         "你也可以直接继续。",
        "setup.two_channel_note": "该设备只有这两个电极，因此没有需要逐个填满的头部图。"
                                  "两个电极都必须变绿，沟通板才会接受选择。",

        "board.composed": "已输入内容：{text}",
        "board.speak": "🔊 朗读",
        "board.backspace": "⌫ 退格",
        "board.pause": "⏸️ 暂停",
        "board.resume": "▶️ 继续",
        "board.exit": "✕ 退出",
        "board.mode": "模式：自动扫描",
        "board.speed": "速度：",
        "board.include_mental": "启用意念指令",
        "board.include_facial": "启用面部表情",
        "board.facial_unsupported": "该头戴设备不支持面部表情",
        "board.mental_sens": "意念灵敏度：{value}",
        "board.facial_sens": "面部灵敏度：{value}",
        "board.cooldown": "冷却时间：{value} 秒",
        "speed.very_slow": "很慢",
        "speed.slow": "慢",
        "speed.medium": "中",
        "speed.fast": "快",
        "speed.very_fast": "很快",

        "controls.both": "{select_thought}/{select_facial} = 选择  •  "
                         "{speed_thought}/{speed_facial} = 调速",
        "controls.mental": "{select_thought} = 选择  •  {speed_thought} = 调速",
        "controls.facial": "{select_facial} = 选择  •  {speed_facial} = 调速",
        "controls.none": "已关闭全部脑机接口控制",

        "telemetry.line": "脑机接口 —— 意念指令状态：{mental}   |   面部肌电状态：{facial}",
        "telemetry.disabled": "已关闭",
        "telemetry.unsupported": "该设备不支持",
        "telemetry.neutral": "中性（待机）[强度：{power}]",
        "telemetry.facial_ready": "就绪（待机）",
        "telemetry.paused": "扫描已暂停",
        "telemetry.below": "{command}（{action}）[强度：{power}]（低于阈值）",
        "telemetry.locked": "{command}（{action}）[强度：{power}]（已锁定）",
        "telemetry.holding": "正在保持 {command}（{action}）… （{elapsed} 秒 / {needed} 秒）",
        "telemetry.triggered": "已触发 {command}！[强度：{power}]",
        "telemetry.triggered_facial": "已触发 {command}（{action} 备用）！[强度：{power}]",
        "telemetry.cooldown": "⏳ 冷却中 —— [{phase}]  |  {seconds} 秒后恢复"
                              "（请放松头脑与面部）",
        "action.select": "选择",
        "action.speed": "调整速度",
        "action.speed_short": "调速",
        "phase.row_locked": "已锁定该行",
        "phase.selection_complete": "选择完成",
        "phase.cancelled": "已取消该行",

        "pill.contact": "接触 {percent}%",
        "pill.eeg": "脑电 {percent}%",
        "pill.battery": "🔋 {percent}%",
        "pill.no_data": "—",
        "pill.warning": "⚠ {names} 信号变差 —— 请检查电极",

        "status.waiting": "正在等待连接…",
        "status.connecting": "正在连接 Cortex 服务…",
        "status.linked": "已连接 Cortex，正在等待设备数据…",
        "status.live": "数据流已连接，正在监测设备状态…",
        "status.loading_profile": "正在加载配置文件：{profile}…",
        "status.failed": "Cortex 连接失败：{detail}",
        "status.no_cortex_file": "找不到 cortex.py 文件。",
        "status.config_error": "读取 config.json 出错：{detail}",
        "status.scanner_active": "扫描进行中。",
        "status.scanner_paused": "扫描已暂停。",
        "status.cooldown": "冷却中（{seconds} 秒）…",
        "status.stream_refused": "Cortex 拒绝了 {stream}：{detail}",

        "cell.YES": "是",
        "cell.NO": "不是",
        "cell.MAYBE": "也许",
        "cell.I DON'T KNOW": "我不知道",
        "cell.THANK YOU": "谢谢",
        "cell.SOMETHING ELSE": "其他",
        "cell.BACKSPACE": "退格",
        "cell.SPEAK": "朗读",
        "cell.SPACE": "空格",
        "cell.PAUSE SCANNER": "暂停扫描",
        "cell.CLEAR MESSAGE": "清空",
        "cell.FLIP OVER": "切换面板",
        "cell.CANCEL": "取消",
        "cell.I HAVE TO TELL YOU SOMETHING": "我有话要说",
        "cell.I LOVE YOU": "我爱你",
        "cell.YOU'RE WELCOME": "不客气",
        "cell.HELLO": "你好",
        "cell.I AM": "我",
        "cell.HAPPY": "开心",
        "cell.SAD": "难过",
        "cell.TIRED": "累",
        "cell.HOT": "热",
        "cell.COLD": "冷",
        "cell.EXCITED": "兴奋",
        "cell.I HAVE A PROBLEM": "我有问题",
        "cell.PAIN": "疼",
        "cell.CRAMP": "抽筋",
        "cell.ITCH": "痒",
        "cell.STOP": "停下",
        "cell.SICK": "不舒服",
        "cell.UNCOMFORTABLE": "难受",
        "cell.I NEED": "我需要",
        "cell.SUCTION": "吸痰",
        "cell.MEDICINE": "药",
        "cell.BATHE": "洗澡",
        "cell.BATHROOM": "上厕所",
        "cell.BED": "床",
        "cell.BREATHING MACHINE": "呼吸机",
        "cell.MASSAGE": "按摩",
        "cell.LEG": "腿",
        "cell.ARM": "手臂",
        "cell.HIPS": "臀部",
        "cell.HEAD": "头",
        "cell.LEFT": "左边",
        "cell.RIGHT": "右边",
        "cell.I WANT": "我想要",
        "cell.FOOD": "吃的",
        "cell.DRINK": "喝的",
        "cell.TV": "电视",
        "cell.PHONE": "手机",
        "cell.COMPUTER": "电脑",
        "cell.HELP": "帮忙",
        "cell.TO GO": "出去",
        "cell.TO CALL": "打电话",
        "cell.A HUG": "抱抱",
        "cell.A KISS": "亲一下",
        "cell.COMPANY": "陪陪我",
        "cell.WAIT": "等一下",
        "cell.PLEASE GUESS": "请猜一下",

        "phrases.title": "看护者自定义短语",
        "phrases.header": "📝 管理沟通板短语",
        "phrases.subtitle": "看护者可以在下面添加日常请求、家人称呼或自定义短语。",
        "phrases.add": "添加短语",
        "phrases.remove": "删除所选",
        "phrases.reset": "恢复默认",
        "phrases.save": "保存",
        "phrases.cancel": "取消",
        "phrases.prompt_title": "新短语",
        "phrases.prompt_body": "要添加到沟通板的短语：",
        "creds.title": "EMOTIV Cortex 凭据",
        "creds.client_id": "Client ID",
        "creds.client_secret": "Client Secret",
        "creds.profile": "配置文件名称",
        "creds.select_thought": "选择 —— 意念指令",
        "creds.select_facial": "选择 —— 面部表情",
        "creds.speed_thought": "调整速度 —— 意念指令",
        "creds.speed_facial": "调整速度 —— 面部表情",
        "creds.include_mental": "启用意念指令",
        "creds.include_facial": "启用面部表情",
        "creds.save": "保存",
        "creds.cancel": "取消",
        "creds.help": "请在 emotiv.com → My Account → Cortex Apps 创建一个应用，"
                      "然后把它的 Client ID 和 Client Secret 填到这里。"
                      "配置文件是要加载的 EMOTIV BCI 训练档案。",
    },
}


def set_language(language: str):
    """Switch language and re-render everything already on screen."""
    global _current
    if language not in STRINGS:
        return
    _current = language
    refresh()


def language() -> str:
    return _current


def t(key: str, **params) -> str:
    """Translate. An unknown key returns itself, which makes it obvious on screen."""
    table = STRINGS.get(_current, STRINGS["en"])
    text = table.get(key, STRINGS["en"].get(key, key))
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError):
            return text
    return text


def cell(token: str) -> str:
    """The label for a board cell.

    A caregiver's own phrase has no entry, so it comes back exactly as typed.
    Single letters and digits are the same in both languages.
    """
    key = "cell." + token
    table = STRINGS.get(_current, STRINGS["en"])
    return table.get(key, token)


def bind(widget, key: str, **params):
    """Set a widget's text now, and again whenever the language changes.

    Re-binding a widget replaces its previous key rather than adding a second
    one — the pause button, for instance, is re-bound every time it flips
    between "pause" and "resume".
    """
    unbind(widget)
    _bound.append((widget, key, params))
    widget.setText(t(key, **params))
    return widget


def unbind(widget):
    """Stop tracking a widget — for labels the app then writes directly."""
    global _bound
    _bound = [entry for entry in _bound if entry[0] is not widget]


def refresh():
    """Re-apply every bound string. Deleted widgets drop out quietly."""
    global _bound
    alive = []
    for widget, key, params in _bound:
        try:
            widget.setText(t(key, **params))
            alive.append((widget, key, params))
        except RuntimeError:
            # The C++ side is gone; the Python wrapper outlived it.
            continue
    _bound = alive
