## Clash Merge

### 简介

这是一个可以自动合并多个订阅的信息，到我们指定的基础 `clash` 配置文件库中的脚本。

可能上面这段话说的不容易理解，我们来举个例子，我们购买了不少服务，每个服务商都提供了一个代理订阅地址，我们不想切换配置文件，想把所有我们购买的服务都合并到一个配置文件，并且采用网络上面维护比较好的规则。

---
* [支持解析的代理规则](#支持解析的代理规则)
* [遇到无法解析](#遇到无法解析)
* [支持的基础规则](#支持的基础规则)
* [配置文件说明](#配置文件说明)
* [使用方法](#使用方法)
* [在线编辑](#在线编辑)
* [Docker 构建与部署](#docker-构建与部署)
* [特别说明](#特别说明)
* [鸣谢](#鸣谢)

---

### 支持解析的规则

目前可以解析 clash 的 yaml 文件，base64 的配置文件（支持 vmess, vless, trojan, ss 等协议）

---

### 遇到无法解析

提 issue

---

### 支持的基础规则
- [x] [Hackl0us](https://github.com/Hackl0us/SS-Rule-Snippet)

[//]: # (- [ ] [ConnersHua]&#40;https://github.com/ConnersHua/Profiles&#41; 由于这个规则修改后用了太多的 core feature ，我在 mac 上没法测试，所以暂时没法测试是否有效。)

---

### 配置文件说明

文件太长，参考 [配置文件说明](config/.config.yaml)。另外需要多说一句，使用之前先看到自己的基础规则都支持啥，配置文件就是为了可以更多的自定义而已，不要一股脑的弄上去，弄坏了也不知道咋回事，多测试测试

---

### 使用方法

1. 依赖环境
   本项目需要 `Python 3` 环境。
   ```bash
   pip install -r requirements.txt
   ```

2. 配置文件
   参考 `config/template.yaml` 修改为 `config/你的配置.yaml`。 最关键的节点是 `pull-proxy-source` 这里面配置的就是你的服务 `订阅链接`。其他的配置其实可以不用改，如果要更改就做好详尽的测试，里面的每个节点在目前支持的基础规则我都保证测试可用，如果你用不了，那就自己好好查查。另外一个节点是 `Proxy` 这里面可以配置你自己搭建的，或者没有配置文件的节点。配置文件里面的内容最终都会合并到配置文件里面去。
   > 注意配置文件要放在运行目录的 `config` 目录下

3. 运行
   在项目根目录下运行：
   ```bash
   python main.py [Port]
   ```
   `Port` 是你服务器要开启的端口，默认为 6789。

4. 访问
   然后访问你的 `http://ip:port/parse?name=你的配置&baseName=BaseRuleName`。 `你的配置` 这个就是上面操作你自己更改的配置文件名称（不包含 `.yaml` 后缀），`BaseRuleName` 这个名字就是在配置文件中 `base-config` 节点下的 `name`。

5. 结果
   如果没问题，就可以看到输出配置文件，如果有问题去 `log/log.txt` 查看日志文件。

### 在线编辑

- 页面入口：`http://ip:port/config/ui`
- 用法：在输入框填入文件名（不带 `.yaml`），点击“加载”获取现有内容；修改后点击“保存”写入 `config/<文件名>.yaml`
- 对应接口：
  - 加载：`GET /config/load?name=<文件名>` 返回 YAML 文本
  - 保存：`POST /config/save?name=<文件名>` 请求体为 YAML 文本

---

### Docker 构建与部署

1. 构建镜像
   在项目根目录执行：
   ```bash
   docker build -t crazybun/mergevpn:2.0 .
   ```

2. 运行容器
   将本地 `config` 目录挂载到容器内，以便读写配置文件：
   ```bash
   cd /root/MergeVPN
   docker run -itd --name mergevpn --restart always -e TZ=Asia/Shanghai -v $(pwd)/config:/app/config -v $(pwd)/log:/app/log -p 6789:6789 crazybun/mergevpn:2.0
   ```

3. 验证服务
   - 解析接口：`http://localhost:6789/parse?name=template&baseName=clash-config`
   - 在线编辑：`http://localhost:6789/config/ui`

4. 常见问题
   - 如果容器内未找到配置文件，请确认已挂载 `config` 目录，并且文件名不包含 `.yaml` 后缀。
   - 日志输出在容器内 `/app/log/log.txt`，可通过 `docker logs pull-merge-config` 查看实时日志。

例如: 

配置文件使用 `config/template.yaml`

配置目录结构如下:

![目录结构](dir.png)

```shell
python main.py 6789
# 服务启动，端口：6789
```

访问 `http://localhost:6789/parse?name=template&baseName=clash-config` 即可获取合并后的 Clash 配置文件
接口路由已拆分，当前 `/parse` 由 `routes/parse.py` 注册蓝图并委托到 `services/parser_service.py` 完成解析与合并。

#### 新增接口指南
- 在 `routes` 新建路由文件，定义 `Blueprint` 与路由；在 `services` 新建对应服务模块实现业务逻辑。
- 在 `main.py` 中 `register_blueprint` 引入新蓝图。
- 示例：
  ```python
  # routes/my.py
  from flask import Blueprint, request
  from services import my_service

  my_bp = Blueprint("my", __name__)

  @my_bp.route("/my", methods=["POST"])
  def create():
      data = request.get_json()
      return my_service.create(data)
  ```
  在 `main.py` 中：
  ```python
  from routes.my import my_bp
  app.register_blueprint(my_bp)
  ```
该地址直接在 Clash 中使用即可，包括订阅的节点以及自定义规则等，详见 [配置文件说明](config/template.yaml)

---

### 特别说明

本版本开始，已经不建议在本地运行，推荐部署在服务器上。因为开启了 http 服务器，可以更长时间的在服务器上运行了，以往的 `crontab` 也不需要了，现在在用实时合并直接输出了，合并会更及时。

这一切都是在满足我的需求为第一前提下弄的，如果能够对你也有用，我深感荣幸。如果你想使用但是遇到了问题，请去提 `issue` 我会在我所知的情况下尽可能的回答。

配置文件中的 `base-config` 节点不要修改，因为你改了代码也不支持，写到配置文件中，仅仅是为了防止他们的地址变动我不用再次编译了而已。 

---

### 鸣谢

- [原作者 crazyhl](https://github.com/crazyhl/PullAndMergeConfig)
- [Hackl0us](https://github.com/Hackl0us)
- [ConnersHua](https://github.com/ConnersHua)

---

### TODO

- [ ] 支持更多协议（vless、hysteria、tuic 等）
- [ ] 添加客户端参数选择（OpenClash、ClashVerge、FlClash 等）
- [ ] 根据客户端能力过滤协议节点（仅保留对应客户端支持的协议）
- [ ] 在线编辑页面增强（快捷键保存、格式化 YAML、深色主题预设）
- [ ] 增加 CI 检查（lint/type-check）与基础单元测试
