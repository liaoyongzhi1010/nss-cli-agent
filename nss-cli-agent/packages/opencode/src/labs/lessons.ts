export interface LessonStep {
  id: string
  title: string
  guidance: string
  completionHint: string
}

export interface LessonScript {
  exerciseID: string
  title: string
  steps: LessonStep[]
}

export const lessonScripts: Record<string, LessonScript> = {
  "crypto-basic": {
    exerciseID: "crypto-basic",
    title: "对称/公钥/哈希/签名：正确使用与误用识别",
    steps: [
      {
        id: "goal",
        title: "理解实验目标",
        guidance:
          "简洁讲清本实验要掌握的四类密码学原语：对称加密(AES)、公钥加密(RSA)、哈希(SHA-256)、数字签名，各自解决什么问题。讲完后问学生一个小问题（如\"你觉得哈希和加密最大的区别是什么？\"），停下等学生回答，答了再进入下一步。",
        completionHint: "学生回应了对四类原语用途的理解",
      },
      {
        id: "principle",
        title: "了解关键原理",
        guidance:
          "讲解 AES 的 IV、填充、认证标签的作用，以及为什么 ECB 不安全（举一个直观例子）。讲完后让学生回答\"为什么同一份明文用 ECB 加密会暴露信息\"，停下等学生回应，再进入下一步。",
        completionHint: "学生回应了对 IV/填充/认证标签和 ECB 风险的理解",
      },
      {
        id: "implement",
        title: "用 AI 生成实现代码",
        guidance:
          "用写文件工具（write/edit）在当前实验目录下**真实创建 solution.py**，用 Python(cryptography 库) 实现四类原语，代码里写清注释。不要只在对话里贴代码——必须把文件写到磁盘，确保学生在实验目录能直接看到并运行。写完后，请学生挑其中一段（如 AES 加密部分）用自己的话说说\"这段在做什么\"，停下等学生回应，确认他看懂了再进入下一步。",
        completionHint: "已在实验目录写出 solution.py，且学生能说明其中某段的作用",
      },
      {
        id: "run",
        title: "运行并验证结果",
        guidance:
          "请学生在实验目录运行 python solution.py，把输出贴回来（solution.py 上一步已真实写入磁盘，可直接运行）。停下等学生贴结果；若报错（如 ModuleNotFoundError: cryptography）就让他先 pip install cryptography 再运行，并帮他定位修复。确认加解密一致、签名验签通过后，再进入下一步。",
        completionHint: "学生贴出了运行结果且正确",
      },
      {
        id: "summary",
        title: "总结要点与误用识别",
        guidance:
          "让学生先尝试说出至少一处常见误用(如 ECB、复用 IV、无认证加密、MD5 签名、固定盐值)，你再补充并讲危害与修复。停下等学生回应；总结到位后告诉学生本实验完成，可用 /lesson 选 report 生成报告。",
        completionHint: "学生参与总结了误用并理解修复",
      },
    ],
  },
  "crypto-inter": {
    exerciseID: "crypto-inter",
    title: "PKI 证书链与 TLS 握手抓包分析",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要搞懂：证书链（根CA→中间CA→站点）如何建立信任，以及 TLS 握手中证书在哪一步被校验。讲完问学生\"为什么浏览器要信任根CA而不是直接信任网站证书\"，停下等回答再继续。", completionHint: "学生回应了对信任链的理解" },
      { id: "principle", title: "了解关键原理", guidance: "讲解 TLS 握手关键步骤（ClientHello/ServerHello、证书下发、密钥协商）与证书校验点（有效期、域名、签发者、吊销）。讲完让学生说\"握手中哪一步最能体现身份认证\"，停下等回应。", completionHint: "学生回应了对握手与校验点的理解" },
      { id: "implement", title: "抓包与证书链解析", guidance: "用写文件工具在实验目录真实创建脚本（如用 Python ssl/socket 拉取目标站点证书链，或用 openssl s_client 命令配合脚本），导出并解析证书链。写完后请学生挑证书的一个字段（如 Subject/Issuer）说说含义，停下等回应。", completionHint: "已写出抓包/解析脚本，学生能解释证书字段" },
      { id: "run", title: "运行并验证结果", guidance: "请学生运行脚本，把证书链输出贴回来。停下等结果；报错帮他定位。确认能看到完整链与各级签发关系后再继续。", completionHint: "学生贴出了证书链解析结果" },
      { id: "summary", title: "总结要点与风险", guidance: "让学生先说一处证书相关风险（如自签证书、过期、域名不匹配、弱签名算法），你再补充危害与防护。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了证书风险" },
    ],
  },
  "crypto-adv": {
    exerciseID: "crypto-adv",
    title: "MITM 构造与信任链失效分析",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验目标：在受控环境理解中间人(MITM)如何利用信任链缺陷，以及正确的证书校验如何阻止它。强调仅在本地/授权环境实验。讲完问\"MITM 想成功，必须骗过证书校验的哪一环\"，停下等回答。", completionHint: "学生回应了 MITM 与信任链关系" },
      { id: "principle", title: "了解关键原理", guidance: "讲解信任链失效的典型场景（用户点击信任未知证书、CA 被攻陷、未做域名校验、降级攻击）。讲完让学生说\"为什么客户端不校验证书等于门户大开\"，停下等回应。", completionHint: "学生回应了信任失效场景" },
      { id: "implement", title: "构造受控演示", guidance: "用写文件工具在实验目录真实创建演示脚本：用自签 CA 模拟\"被信任的恶意证书\"，演示校验开启/关闭两种客户端行为差异（仅本地回环）。写完请学生指出代码里哪行决定了是否校验证书，停下等回应。", completionHint: "已写出受控演示脚本，学生能定位校验开关" },
      { id: "run", title: "运行并对比结果", guidance: "请学生分别在\"校验开启/关闭\"下运行并贴出结果对比。停下等结果；帮他解读为何关闭校验时 MITM 才得逞。", completionHint: "学生贴出了两种校验下的对比结果" },
      { id: "summary", title: "总结防御要点", guidance: "让学生先说该如何防御 MITM（强制校验、证书钉扎、HSTS、不信任未知CA），你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了 MITM 防御" },
    ],
  },
  "web-sec-basic": {
    exerciseID: "web-sec-basic",
    title: "SQLi/XSS/CSRF 复现与最小修复",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清三类经典 Web 漏洞 SQLi/XSS/CSRF 各自利用了什么、危害是什么。讲完问学生\"这三者里哪个是'让浏览器替你发请求'\"，停下等回答再继续。", completionHint: "学生回应了三类漏洞的区别" },
      { id: "principle", title: "了解关键原理", guidance: "讲解每类漏洞的成因（拼接 SQL、未转义输出、缺少 CSRF token/SameSite）。讲完让学生说\"SQLi 的根因是数据被当成了什么\"，停下等回应。", completionHint: "学生回应了漏洞成因" },
      { id: "implement", title: "复现与最小修复", guidance: "用写文件工具在实验目录真实创建一个最小可复现的小应用（如 Flask + SQLite），先写出有漏洞版本，再写修复版本（参数化查询、输出转义、CSRF token）。写完请学生对比修复前后差异说一处关键改动，停下等回应。", completionHint: "已写出漏洞与修复版本，学生能说出关键改动" },
      { id: "run", title: "运行并验证", guidance: "请学生运行应用，先复现漏洞再验证修复后被挡，把现象贴回来。停下等结果；报错帮他定位（含 pip 装依赖）。", completionHint: "学生贴出了复现与修复验证结果" },
      { id: "summary", title: "总结防御要点", guidance: "让学生先说每类漏洞的标准防御，你再补全（参数化、转义、CSP、SameSite、最小权限）。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了三类防御" },
    ],
  },
  "web-sec-inter": {
    exerciseID: "web-sec-inter",
    title: "容器化部署 + 日志审计与防护配置",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要掌握：把 Web 应用容器化部署，并通过日志审计 + 防护配置提升安全性。讲完问学生\"日志审计在安全中主要解决'事前事中事后'的哪一环\"，停下等回答。", completionHint: "学生回应了日志审计的作用" },
      { id: "principle", title: "了解关键原理", guidance: "讲解容器最小化（非 root、只读文件系统、最小镜像）、关键日志（访问日志、错误日志、审计点）与基础防护（限流、安全响应头）。讲完让学生说一条容器安全配置原则，停下等回应。", completionHint: "学生回应了容器安全原则" },
      { id: "implement", title: "编写部署与配置", guidance: "用写文件工具在实验目录真实创建 Dockerfile + 应用 + 日志/防护配置（非 root 用户、安全响应头、访问日志）。写完请学生指出 Dockerfile 里哪行降低了权限风险，停下等回应。", completionHint: "已写出 Dockerfile 与配置，学生能定位安全配置" },
      { id: "run", title: "构建运行并查日志", guidance: "请学生构建并运行容器、访问应用并查看产生的日志，把日志片段贴回来。停下等结果；docker 报错帮他定位。", completionHint: "学生贴出了运行与日志结果" },
      { id: "summary", title: "总结审计与防护", guidance: "让学生先说哪些事件最该记入审计日志，你再补充防护清单。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了审计与防护" },
    ],
  },
  "web-sec-adv": {
    exerciseID: "web-sec-adv",
    title: "多框架/多配置变体：对比防护效果与代价",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要做的事：对同一类防护在不同框架/配置下做对比，权衡安全收益与代价（性能、复杂度）。讲完问学生\"安全加固为什么不是'越多越好'\"，停下等回答。", completionHint: "学生回应了安全与代价的权衡" },
      { id: "principle", title: "了解关键原理", guidance: "讲解对比实验该控制什么变量、用什么指标衡量防护效果与代价。讲完让学生说一个能量化'代价'的指标（如延迟、吞吐、配置复杂度），停下等回应。", completionHint: "学生回应了对比指标" },
      { id: "implement", title: "搭建对比变体", guidance: "用写文件工具在实验目录真实创建至少两个配置变体（如开启/关闭某防护，或两种框架实现）及对比脚本。写完请学生说两个变体的关键差异，停下等回应。", completionHint: "已写出多个变体与对比脚本，学生能说出差异" },
      { id: "run", title: "运行对比并记录", guidance: "请学生运行各变体、记录防护效果与代价指标，把对比数据贴回来。停下等结果；帮他解读数据。", completionHint: "学生贴出了对比数据" },
      { id: "summary", title: "总结取舍建议", guidance: "让学生先给出'在什么场景选哪个变体'的建议，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了取舍建议" },
    ],
  },
  "os-sec-basic": {
    exerciseID: "os-sec-basic",
    title: "权限边界与 Set-UID：安全配置与风险点",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要掌握：Unix 权限模型（用户/组/其他、rwx）与 Set-UID 机制及其风险。讲完问学生\"Set-UID 程序运行时用的是谁的权限\"，停下等回答。", completionHint: "学生回应了 Set-UID 的权限语义" },
      { id: "principle", title: "了解关键原理", guidance: "讲解最小权限原则、Set-UID 为何危险（提权面）、常见误配。讲完让学生说\"为什么给脚本随意加 Set-UID 很危险\"，停下等回应。", completionHint: "学生回应了 Set-UID 风险" },
      { id: "implement", title: "演示权限与 Set-UID", guidance: "用写文件工具在实验目录真实创建演示脚本（创建文件并用 chmod 演示权限位、展示 Set-UID 位的效果与风险，仅本地）。写完请学生解释某条 chmod 的含义，停下等回应。", completionHint: "已写出权限演示脚本，学生能解释权限位" },
      { id: "run", title: "运行并观察", guidance: "请学生运行脚本、用 ls -l 观察权限位变化，把输出贴回来。停下等结果；帮他读懂权限位。", completionHint: "学生贴出了权限观察结果" },
      { id: "summary", title: "总结安全配置", guidance: "让学生先说如何安全地配置权限（最小权限、避免滥用 Set-UID），你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了权限安全配置" },
    ],
  },
  "os-sec-inter": {
    exerciseID: "os-sec-inter",
    title: "环境变量/命令注入：复现与防护",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验目标：理解命令注入与环境变量滥用如何导致任意命令执行，并掌握防护。讲完问学生\"命令注入的根因和 SQLi 有什么相似之处\"，停下等回答。", completionHint: "学生回应了命令注入根因" },
      { id: "principle", title: "了解关键原理", guidance: "讲解 shell 拼接的危险、不可信输入进入命令的路径、环境变量(如 PATH/LD_PRELOAD)被污染的风险。讲完让学生说一种避免拼接命令的做法，停下等回应。", completionHint: "学生回应了防护思路" },
      { id: "implement", title: "复现与修复", guidance: "用写文件工具在实验目录真实创建可复现命令注入的小脚本（仅本地），再写修复版本（参数化执行、白名单、避免 shell=True）。写完请学生指出修复版关键改动，停下等回应。", completionHint: "已写出复现与修复脚本，学生能定位改动" },
      { id: "run", title: "运行并验证", guidance: "请学生运行复现注入、再验证修复后被挡，把现象贴回来。停下等结果；帮他定位。", completionHint: "学生贴出了复现与修复结果" },
      { id: "summary", title: "总结防护要点", guidance: "让学生先说命令注入的标准防护，你再补全（避免拼接、参数化、最小权限、清理环境变量）。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了防护要点" },
    ],
  },
  "os-sec-adv": {
    exerciseID: "os-sec-adv",
    title: "TOCTOU 竞态条件：机制理解 + 证据链",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清 TOCTOU(检查时到使用时)竞态的本质：检查与使用之间状态被改变。讲完问学生\"为什么'先检查文件再打开'可能不安全\"，停下等回答。", completionHint: "学生回应了 TOCTOU 本质" },
      { id: "principle", title: "了解关键原理", guidance: "讲解竞态窗口、符号链接攻击、原子操作的意义。讲完让学生说\"如何用原子操作消除竞态窗口\"，停下等回应。", completionHint: "学生回应了原子操作思路" },
      { id: "implement", title: "演示竞态与修复", guidance: "用写文件工具在实验目录真实创建演示脚本（构造检查-使用窗口，仅本地），再写修复版（用原子打开/文件描述符而非路径重复访问）。写完请学生解释竞态窗口在代码哪两步之间，停下等回应。", completionHint: "已写出竞态演示与修复，学生能定位窗口" },
      { id: "run", title: "运行并形成证据链", guidance: "请学生运行演示、记录关键时序与现象作为证据，把输出贴回来。停下等结果；帮他解读时序。", completionHint: "学生贴出了竞态证据" },
      { id: "summary", title: "总结防御与证据", guidance: "让学生先说防御竞态的方法，你再补充并强调证据链记录。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了竞态防御" },
    ],
  },
  "db-sec-basic": {
    exerciseID: "db-sec-basic",
    title: "注入风险与最小权限原则",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验目标：理解数据库注入风险与最小权限原则。讲完问学生\"应用连库账号该不该用管理员权限\"，停下等回答。", completionHint: "学生回应了最小权限意识" },
      { id: "principle", title: "了解关键原理", guidance: "讲解参数化查询、账号权限分离、敏感数据访问控制。讲完让学生说\"参数化查询为什么能防注入\"，停下等回应。", completionHint: "学生回应了参数化原理" },
      { id: "implement", title: "演示注入与防护", guidance: "用写文件工具在实验目录真实创建脚本：演示拼接 SQL 的注入（本地 SQLite），再写参数化的安全版本，并演示按最小权限建账号的思路。写完请学生指出安全版关键改动，停下等回应。", completionHint: "已写出注入与防护脚本，学生能定位改动" },
      { id: "run", title: "运行并验证", guidance: "请学生运行复现注入、再验证参数化版本安全，把现象贴回来。停下等结果；帮他定位。", completionHint: "学生贴出了验证结果" },
      { id: "summary", title: "总结安全实践", guidance: "让学生先说数据库安全的核心实践，你再补全（参数化、最小权限、审计、加密）。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了数据库安全实践" },
    ],
  },
  "db-sec-inter": {
    exerciseID: "db-sec-inter",
    title: "账号权限/备份/日志泄露/凭据管理",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验涵盖：账号权限分级、备份安全、日志中的敏感信息泄露、凭据管理。讲完问学生\"日志里打印完整密码/令牌会有什么风险\"，停下等回答。", completionHint: "学生回应了日志泄露风险" },
      { id: "principle", title: "了解关键原理", guidance: "讲解权限分级、备份加密与隔离、日志脱敏、凭据用密钥管理/环境变量而非硬编码。讲完让学生说一种凭据管理的正确做法，停下等回应。", completionHint: "学生回应了凭据管理做法" },
      { id: "implement", title: "演示配置与脱敏", guidance: "用写文件工具在实验目录真实创建脚本/配置：演示日志脱敏、凭据从环境变量读取、备份文件权限收紧。写完请学生指出哪行实现了脱敏，停下等回应。", completionHint: "已写出脱敏与凭据管理脚本，学生能定位" },
      { id: "run", title: "运行并验证", guidance: "请学生运行，确认日志中敏感信息被脱敏、凭据未硬编码，把现象贴回来。停下等结果。", completionHint: "学生贴出了脱敏验证结果" },
      { id: "summary", title: "总结治理要点", guidance: "让学生先说一套凭据/日志治理清单，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了治理要点" },
    ],
  },
  "db-sec-adv": {
    exerciseID: "db-sec-adv",
    title: "功能需求→安全约束：配置方案设计与验证",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要做的事：给定功能需求，推导出安全约束，并设计可验证的数据库配置方案。讲完问学生\"功能需求和安全约束有时会冲突，怎么权衡\"，停下等回答。", completionHint: "学生回应了需求与约束权衡" },
      { id: "principle", title: "了解关键原理", guidance: "讲解从需求映射到权限/加密/审计约束的方法论。讲完让学生举一个'需求→约束'的例子，停下等回应。", completionHint: "学生回应了映射方法" },
      { id: "implement", title: "设计并实现配置", guidance: "用写文件工具在实验目录真实创建配置方案与验证脚本（角色权限、访问控制、审计点）。写完请学生说方案中一条约束对应哪个需求，停下等回应。", completionHint: "已写出配置方案与验证脚本，学生能对应需求" },
      { id: "run", title: "运行验证约束", guidance: "请学生运行验证脚本，确认约束生效（如越权访问被拒），把结果贴回来。停下等结果。", completionHint: "学生贴出了约束验证结果" },
      { id: "summary", title: "总结设计取舍", guidance: "让学生先说方案的安全-功能取舍，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了设计取舍" },
    ],
  },
  "sw-sec-basic": {
    exerciseID: "sw-sec-basic",
    title: "缓冲区溢出/格式化字符串：漏洞机理",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要理解缓冲区溢出与格式化字符串漏洞的机理（仅机理与受控演示，不做真实攻击）。讲完问学生\"栈溢出为什么能改变程序执行流\"，停下等回答。", completionHint: "学生回应了溢出基本机理" },
      { id: "principle", title: "了解关键原理", guidance: "讲解栈帧布局、返回地址、%n 等格式化串风险。讲完让学生说\"为什么不可信输入不能直接作为 printf 的格式串\"，停下等回应。", completionHint: "学生回应了格式化串风险" },
      { id: "implement", title: "受控演示代码", guidance: "用写文件工具在实验目录真实创建最小 C 示例（演示溢出/格式化串机理，编译时可关防护用于教学，仅本地），并附安全写法对照。写完请学生指出不安全函数（如 gets/strcpy）在哪，停下等回应。", completionHint: "已写出演示与安全对照代码，学生能定位不安全函数" },
      { id: "run", title: "编译运行观察", guidance: "请学生编译运行（gcc），观察溢出/异常现象，把输出贴回来。停下等结果；编译报错帮他定位。", completionHint: "学生贴出了编译运行结果" },
      { id: "summary", title: "总结防护机制", guidance: "让学生先说有哪些缓解机制（边界检查、安全函数、ASLR/Canary/NX），你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了防护机制" },
    ],
  },
  "sw-sec-inter": {
    exerciseID: "sw-sec-inter",
    title: "ASLR/Canary/NX 防护机制对比验证",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要对比验证三种二进制防护：ASLR、Canary、NX 各自防什么。讲完问学生\"NX 主要阻止的是哪类攻击行为\"，停下等回答。", completionHint: "学生回应了三种防护的作用" },
      { id: "principle", title: "了解关键原理", guidance: "讲解 ASLR(地址随机化)、Stack Canary(栈溢出检测)、NX(数据页不可执行)的机制与互补关系。讲完让学生说\"为什么需要多种防护叠加\"，停下等回应。", completionHint: "学生回应了防护互补性" },
      { id: "implement", title: "编写对比实验", guidance: "用写文件工具在实验目录真实创建脚本/小程序与编译选项，分别开关 ASLR/Canary/NX 做对比（仅本地教学）。写完请学生说某个编译开关对应哪种防护，停下等回应。", completionHint: "已写出对比实验，学生能对应编译开关" },
      { id: "run", title: "运行对比并记录", guidance: "请学生在不同防护开关下运行、记录行为差异，把对比贴回来。停下等结果；帮他解读。", completionHint: "学生贴出了防护对比结果" },
      { id: "summary", title: "总结防护组合", guidance: "让学生先给出推荐的防护组合及理由，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了防护组合" },
    ],
  },
  "sw-sec-adv": {
    exerciseID: "sw-sec-adv",
    title: "给定二进制与约束：最小复现 + 关键步骤解释",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要做的事：在给定二进制与约束下，做最小复现并解释关键步骤（教学/分析向，不鼓励真实攻击）。讲完问学生\"最小复现相比完整利用有什么分析价值\"，停下等回答。", completionHint: "学生回应了最小复现的价值" },
      { id: "principle", title: "了解关键原理", guidance: "讲解分析二进制的基本方法（静态查看、识别危险函数、约束建模）。讲完让学生说一种识别潜在漏洞点的线索，停下等回应。", completionHint: "学生回应了分析线索" },
      { id: "implement", title: "编写分析脚本", guidance: "用写文件工具在实验目录真实创建分析/复现脚本（在受控约束内，仅本地教学）。写完请学生解释脚本关键一步在做什么，停下等回应。", completionHint: "已写出分析脚本，学生能解释关键步骤" },
      { id: "run", title: "运行并记录步骤", guidance: "请学生运行、记录关键步骤与现象，把结果贴回来。停下等结果；帮他解读。", completionHint: "学生贴出了复现步骤记录" },
      { id: "summary", title: "总结与修复建议", guidance: "让学生先给出对应的修复/加固建议，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了修复建议" },
    ],
  },
  "net-sec-basic": {
    exerciseID: "net-sec-basic",
    title: "嗅探与伪造：DNS/TCP 典型攻击",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要理解网络嗅探与伪造（DNS 欺骗、TCP 伪造）的原理（仅本地/授权环境）。讲完问学生\"为什么明文协议容易被嗅探和伪造\"，停下等回答。", completionHint: "学生回应了明文协议风险" },
      { id: "principle", title: "了解关键原理", guidance: "讲解 DNS 查询/响应可被伪造、TCP 序列号与会话伪造、为何需要加密与认证。讲完让学生说\"DNS 欺骗成功的关键前提\"，停下等回应。", completionHint: "学生回应了 DNS 欺骗前提" },
      { id: "implement", title: "受控演示脚本", guidance: "用写文件工具在实验目录真实创建演示脚本（在本地回环/受控环境模拟嗅探与伪造，禁止对真实网络）。写完请学生指出脚本里哪步体现了'伪造'，停下等回应。", completionHint: "已写出受控演示脚本，学生能定位伪造步骤" },
      { id: "run", title: "运行并观察", guidance: "请学生在受控环境运行、观察嗅探/伪造现象，把输出贴回来。停下等结果；帮他解读。", completionHint: "学生贴出了演示结果" },
      { id: "summary", title: "总结防护手段", guidance: "让学生先说防护手段（DNSSEC、加密、随机化、认证），你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了网络防护" },
    ],
  },
  "net-sec-inter": {
    exerciseID: "net-sec-inter",
    title: "防火墙策略探索 + VPN 机制与验证",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要掌握：防火墙策略(允许/拒绝/默认拒绝)与 VPN 的基本机制。讲完问学生\"防火墙'默认拒绝'相比'默认允许'安全在哪\"，停下等回答。", completionHint: "学生回应了默认拒绝的意义" },
      { id: "principle", title: "了解关键原理", guidance: "讲解包过滤规则顺序、状态防火墙、VPN 的加密隧道与认证。讲完让学生说\"VPN 主要保护通信的什么属性\"，停下等回应。", completionHint: "学生回应了 VPN 保护目标" },
      { id: "implement", title: "编写规则与验证", guidance: "用写文件工具在实验目录真实创建防火墙规则脚本（如 iptables/nft 规则文件，仅本地教学）与验证脚本。写完请学生解释一条规则的含义，停下等回应。", completionHint: "已写出规则与验证脚本，学生能解释规则" },
      { id: "run", title: "运行并验证策略", guidance: "请学生应用规则并验证允许/拒绝是否符合预期，把结果贴回来。停下等结果；帮他定位。", completionHint: "学生贴出了策略验证结果" },
      { id: "summary", title: "总结策略要点", guidance: "让学生先给出一套最小化放行的策略思路，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了防火墙策略" },
    ],
  },
  "net-sec-adv": {
    exerciseID: "net-sec-adv",
    title: "容器化拓扑注入网络条件：评估协议鲁棒性",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要做的事：用容器搭建网络拓扑，注入网络条件(丢包/延迟/乱序)评估协议鲁棒性。讲完问学生\"为什么要在受控条件下测协议鲁棒性\"，停下等回答。", completionHint: "学生回应了鲁棒性测试意义" },
      { id: "principle", title: "了解关键原理", guidance: "讲解网络损伤注入(如 tc netem)、容器网络、衡量鲁棒性的指标。讲完让学生说一个能反映协议鲁棒性的指标，停下等回应。", completionHint: "学生回应了鲁棒性指标" },
      { id: "implement", title: "搭建拓扑与注入", guidance: "用写文件工具在实验目录真实创建容器拓扑与网络条件注入脚本（compose + tc 规则，仅本地）。写完请学生说哪行注入了网络损伤，停下等回应。", completionHint: "已写出拓扑与注入脚本，学生能定位注入" },
      { id: "run", title: "运行并采集指标", guidance: "请学生运行、在不同网络条件下采集协议表现，把数据贴回来。停下等结果；帮他解读。", completionHint: "学生贴出了鲁棒性数据" },
      { id: "summary", title: "总结鲁棒性结论", guidance: "让学生先给出协议在何种条件下退化最明显的结论，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了鲁棒性结论" },
    ],
  },
  "tpm-basic": {
    exerciseID: "tpm-basic",
    title: "PCR 度量/对象概念/工具链入门",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要入门 TPM：PCR 度量、TPM 对象概念、工具链(tpm2-tools)。讲完问学生\"PCR 值是怎么随系统状态变化的\"，停下等回答。", completionHint: "学生回应了 PCR 度量概念" },
      { id: "principle", title: "了解关键原理", guidance: "讲解 PCR 扩展(extend)的不可逆累积、度量链、TPM 对象(密钥/句柄)。讲完让学生说\"为什么 PCR 用扩展而不是直接写值\"，停下等回应。", completionHint: "学生回应了 PCR 扩展原理" },
      { id: "implement", title: "工具链操作脚本", guidance: "用写文件工具在实验目录真实创建脚本，调用 tpm2-tools(或软件 TPM 模拟器 swtpm)读取 PCR、做 extend 演示。写完请学生解释脚本中读取 PCR 的命令，停下等回应。", completionHint: "已写出 TPM 工具脚本，学生能解释命令" },
      { id: "run", title: "运行并观察 PCR", guidance: "请学生运行、观察 PCR 在 extend 前后的变化，把输出贴回来。停下等结果；环境缺失则指导用 swtpm 模拟。", completionHint: "学生贴出了 PCR 变化结果" },
      { id: "summary", title: "总结度量价值", guidance: "让学生先说 PCR 度量在可信启动中的价值，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了度量价值" },
    ],
  },
  "tpm-inter": {
    exerciseID: "tpm-inter",
    title: "密封/解封/策略绑定（状态绑定密钥）",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要掌握 TPM 的密封(seal)/解封(unseal)与策略绑定：把密钥绑定到特定系统状态。讲完问学生\"为什么把密钥绑定到 PCR 状态能提升安全\"，停下等回答。", completionHint: "学生回应了状态绑定意义" },
      { id: "principle", title: "了解关键原理", guidance: "讲解密封数据只能在满足策略(如特定 PCR 值)时解封、策略授权(policy)机制。讲完让学生说\"系统被篡改后为何解封会失败\"，停下等回应。", completionHint: "学生回应了策略绑定原理" },
      { id: "implement", title: "密封解封脚本", guidance: "用写文件工具在实验目录真实创建脚本，用 tpm2-tools/swtpm 演示按 PCR 策略密封一段数据并尝试解封。写完请学生指出绑定策略的关键命令，停下等回应。", completionHint: "已写出密封解封脚本，学生能定位策略命令" },
      { id: "run", title: "运行并验证策略", guidance: "请学生运行，验证状态匹配时可解封、改变状态后解封失败，把现象贴回来。停下等结果。", completionHint: "学生贴出了密封/解封验证结果" },
      { id: "summary", title: "总结应用场景", guidance: "让学生先说状态绑定密钥的应用场景(如全盘加密解锁)，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了应用场景" },
    ],
  },
  "tpm-adv": {
    exerciseID: "tpm-adv",
    title: "最小远程证明闭环：Quote/Verify 语义分析",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要搭建最小远程证明(Remote Attestation)闭环并分析 Quote/Verify 语义。讲完问学生\"远程证明想向验证方证明什么\"，停下等回答。", completionHint: "学生回应了远程证明目标" },
      { id: "principle", title: "了解关键原理", guidance: "讲解 Quote(对 PCR 的签名报告)、nonce 防重放、验证方如何校验签名与 PCR 期望值。讲完让学生说\"nonce 在证明中的作用\"，停下等回应。", completionHint: "学生回应了 nonce 作用" },
      { id: "implement", title: "证明闭环脚本", guidance: "用写文件工具在实验目录真实创建脚本，用 tpm2-tools/swtpm 生成 Quote 并在验证侧校验(签名+PCR+nonce)。写完请学生解释验证侧检查了哪几项，停下等回应。", completionHint: "已写出证明闭环脚本，学生能说出校验项" },
      { id: "run", title: "运行并验证闭环", guidance: "请学生运行完整 Quote→Verify，把验证结果贴回来；可尝试改 nonce/PCR 看验证失败。停下等结果。", completionHint: "学生贴出了证明验证结果" },
      { id: "summary", title: "总结语义与局限", guidance: "让学生先说远程证明能证明什么、不能证明什么，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了证明语义与局限" },
    ],
  },
  "tee-basic": {
    exerciseID: "tee-basic",
    title: "环境部署与基本示例跑通（OP-TEE on QEMU）",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要在 QEMU 上部署 OP-TEE 并跑通基本示例，理解 TEE(可信执行环境)是什么。讲完问学生\"TEE 想保护的是什么，免受谁的访问\"，停下等回答。", completionHint: "学生回应了 TEE 保护目标" },
      { id: "principle", title: "了解关键原理", guidance: "讲解普通世界(REE)与可信世界(TEE)隔离、CA(客户端应用)与 TA(可信应用)的概念。讲完让学生说\"为什么敏感操作要放进 TA\"，停下等回应。", completionHint: "学生回应了 REE/TEE 隔离" },
      { id: "implement", title: "部署与示例脚本", guidance: "用写文件工具在实验目录真实创建部署/运行脚本与说明（拉起 OP-TEE on QEMU 并运行官方 hello world 示例）。写完请学生解释脚本里启动 QEMU 的关键参数，停下等回应。", completionHint: "已写出部署脚本，学生能解释关键参数" },
      { id: "run", title: "运行示例", guidance: "请学生跑通示例(如 optee_example_hello_world)，把输出贴回来。停下等结果；环境问题帮他定位。", completionHint: "学生贴出了示例运行结果" },
      { id: "summary", title: "总结 TEE 价值", guidance: "让学生先说 TEE 在真实场景的价值(如密钥保护、指纹支付)，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了 TEE 价值" },
    ],
  },
  "tee-inter": {
    exerciseID: "tee-inter",
    title: "CA-TA 调用链路 + 共享内存与边界分析",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要分析 CA→TA 的调用链路与共享内存机制，理解信任边界。讲完问学生\"CA 和 TA 之间传数据为什么要走受控的共享内存\"，停下等回答。", completionHint: "学生回应了调用链路概念" },
      { id: "principle", title: "了解关键原理", guidance: "讲解 CA 通过 invoke command 调用 TA、参数与共享内存传递、世界切换的边界检查。讲完让学生说\"信任边界在哪、谁不可信\"，停下等回应。", completionHint: "学生回应了信任边界" },
      { id: "implement", title: "编写 CA/TA 示例", guidance: "用写文件工具在实验目录真实创建一个最小 CA+TA 示例(基于 OP-TEE 示例改写)，演示参数与共享内存传递。写完请学生指出哪里是 CA 调 TA 的入口，停下等回应。", completionHint: "已写出 CA/TA 示例，学生能定位调用入口" },
      { id: "run", title: "运行调用链", guidance: "请学生编译运行、观察 CA→TA 调用与返回，把输出贴回来。停下等结果；帮他定位构建问题。", completionHint: "学生贴出了调用链运行结果" },
      { id: "summary", title: "总结边界要点", guidance: "让学生先说跨边界传数据要注意什么(校验、最小暴露)，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了边界要点" },
    ],
  },
  "tee-adv": {
    exerciseID: "tee-adv",
    title: "关键步骤入 TA：敏感数据生命周期与最小暴露证据",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "讲清本实验要做的事：把关键步骤迁入 TA，分析敏感数据生命周期并给出最小暴露的证据。讲完问学生\"敏感数据为什么要尽量只在 TA 内出现\"，停下等回答。", completionHint: "学生回应了最小暴露原则" },
      { id: "principle", title: "了解关键原理", guidance: "讲解敏感数据从产生→使用→销毁的生命周期、在 REE 暴露的风险、如何论证最小暴露。讲完让学生说\"如何证明某敏感数据从未进入普通世界\"，停下等回应。", completionHint: "学生回应了生命周期分析" },
      { id: "implement", title: "迁移关键步骤入 TA", guidance: "用写文件工具在实验目录真实创建示例，把一处敏感处理迁入 TA，并记录数据流证据(哪些只在 TA 内)。写完请学生指出哪步把敏感数据留在了 TA 内，停下等回应。", completionHint: "已写出迁移示例，学生能定位敏感步骤" },
      { id: "run", title: "运行并采集证据", guidance: "请学生运行、采集敏感数据未暴露到 REE 的证据，把结果贴回来。停下等结果；帮他解读。", completionHint: "学生贴出了最小暴露证据" },
      { id: "summary", title: "总结安全论证", guidance: "让学生先给出'敏感数据最小暴露'的论证要点，你再补充。停下等回应；到位后告诉学生用 /lesson 选 report 生成报告。", completionHint: "学生参与总结了安全论证" },
    ],
  },
}

export function getLessonScript(exerciseID: string): LessonScript | undefined {
  return lessonScripts[exerciseID]
}

export function lessonScriptFromDir(directory: string): LessonScript | undefined {
  const base = directory.split(/[\\/]/).filter(Boolean).pop()
  if (!base) return undefined
  const match = base.match(/^\d+-(.+)$/)
  const exerciseID = match ? match[1] : base
  return lessonScripts[exerciseID]
}

export function formatLessonGuidance(script: LessonScript): string {
  const stepLines = script.steps
    .map((step, i) => `${i + 1}. [${step.id}] ${step.title}\n   引导：${step.guidance}\n   完成标志：${step.completionHint}`)
    .join("\n")
  return [
    `# 当前实验引导教学（强互动模式）`,
    ``,
    `学生正在做实验「${script.title}」。你是引导式教学助手。本平台的目标是让学生**真正逐步参与**实验、理解每一步，而不是看你一口气做完。`,
    ``,
    `教学步骤：`,
    stepLines,
    ``,
    `## 最重要的规则：一次只走一步，每步都要停下来等学生`,
    `- 一条回复只处理**当前这一步**。讲解/演示完当前步骤后，必须向学生抛出 1 个具体的问题或动手要求（如"你觉得 ECB 为什么不安全？""请你运行一下这段代码，把输出贴给我"），然后**停止输出，等待学生回复**。`,
    `- **严禁**在学生还没回复的情况下，自己连续推进多个步骤、或把后面几步一次性做完。`,
    `- 只有当学生对当前步骤做出了实质回应（回答了问题 / 完成了操作 / 表示理解）后，才能进入下一步。`,
    ``,
    `## 关于 todo / 任务清单`,
    `- 不要用任务清单把整个实验的多步一次性铺开并自动逐个执行。如果要展示进度，最多标记"当前进行到第几步"，且推进必须由学生的回复驱动，绝不自动连跳。`,
    ``,
    `## 风格`,
    `- 讲解简洁，但每步都要留一个让学生参与的钩子（提问或动手）。`,
    `- 鼓励学生用 AI 生成代码（我们就是 AI 教学平台），但生成后要让学生看懂、能回答"这段在做什么"，再继续。`,
    `- 若学生想直接跳过全过程（如"直接把整个实验做完给我"），明确告诉他：本课程要求逐步参与，请先回应当前这一步。`,
    `- 从第 1 步开始。讲完第 1 步 → 提问 → 停下等学生。`,
  ].join("\n")
}
