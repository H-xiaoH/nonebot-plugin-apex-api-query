<div align="center">
  <a href="https://v2.nonebot.dev/store">
    <img src="./docs/NoneBotPlugin.svg" width="300" alt="logo">
  </a>
</div>

<div align="center">

# NoneBot-Plugin-Apex-API-Query

_✨ 基于 NoneBot 的 Apex Legends API 查询插件 ✨_


<a href="https://registry.nonebot.dev/plugin/nonebot-plugin-apex-api-query:nonebot_plugin_apex_api_query">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fnbbdg.lgc2333.top%2Fplugin%2Fnonebot-plugin-apex-api-query" alt="NoneBot Registry" />
</a>

</div>

## 📖 介绍

基于 NoneBot2 的 [Apex Legends API](https://apexlegendsstatus.com/) 查询插件。

您可以在 [此处](https://portal.apexlegendsapi.com/) 申请您自己的 API 密钥。

申请密钥后重新在 [此页面](https://portal.apexlegendsapi.com/) 登录 API 密钥以测试密钥是否可用。

必须将此 API 密钥 [链接](https://portal.apexlegendsapi.com/discord-auth) 至您的 Discord 账户后您的 API 密钥才可用。

由于 API 的问题，您只能在查询玩家信息时使用 EA 账户用户名并非 Steam 账户用户名。

数据由 API 提供，本插件仅作 数据获取 和 内容转换 。

## 💿 安装

<details>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot_plugin_apex_api_query

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot_plugin_apex_api_query
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot_plugin_apex_api_query
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_apex_api_query"]

</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

```env
APEX_API_KEY = "你的 API 密钥"
```

## 🎉 使用
### 指令表

```shell
apex [玩家名称] [平台] #根据玩家名称查询玩家信息
apex [m|map|地图] #查询地图信息
apex [s|server|服务器] #查询服务器状态
apex [p|predator|顶猎] #查询顶猎分数
```

## 💖 鸣谢

- [@nonebot](https://github.com/nonebot) 强大的 [NoneBot2 机器人框架](https://github.com/nonebot/nonebot2)

## 📄 许可证

本项目使用 [MIT](./LICENSE) 许可证开源

```text
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
