# 小鹤音形 · fcitx5-rime 配置生成器

使用 cubercsl 的小鹤音形词表和拆字反查，叠加 Openfly 的快符、提示与选词习惯。配置源位于 profile/，个人词条位于仓库外。上游说明见 [.github/README.md](.github/README.md)。

## 生成与部署

在 Linux 上安装 GNU Make、Python 3、PyYAML、ruamel.yaml、librime 与 rime_deployer、Rime 基础数据、OpenCC 和 librime-lua。桌面部署还需要 fcitx5-rime 与 busctl。本机验证环境为 librime 1.17.0、PyYAML 6.0.3。

```sh
make generate       # 生成 build/generated/，供检查或打包
make verify         # 还原主词表、对比两次生成结果、从空缓存编译三个方案
make deploy         # 安装到当前用户，写入 fcitx5 的 Rime 前端设置并重载 Rime
```

默认安装目录为 XDG_DATA_HOME 下的 fcitx5/rime。可用下面的命令在独立目录安装和编译，不接触运行中的输入法。

```sh
make install-user USER_RIME_DIR=/tmp/flypy-test PROFILE_DIR=/tmp/empty-profile
```

相同 Git 提交、相同版本的 YAML 库、相同个人输入会生成相同的配置文件。仓库内已经包含基础 YAML 词表，日常生成可离线运行。词库编译还使用本机 SHARED_RIME_DIR（默认 /usr/share/rime-data）；二进制缓存与运行状态单独处理。安装会替换本项目的同名配置，个人源文件放在下节的目录中。安装器接受普通目录，迁移旧的目录软链接时应先保留备份。

如需从同版官方鼠须管包独立核对词库，解压后执行下列命令。该目标用上游脚本从二进制和文本重新生成词表，再与本仓库逐文件比较。官方包由使用者提供。

```sh
make verify-official SOURCE_DIR=/path/to/official/rime
```

## 个人词库

编辑 `~/.config/rime-flypy/personal.yaml`（遵循 XDG_CONFIG_HOME）。普通词和菜单放在 `words`，置顶词放在 `top`，屏蔽项放在 `delete`。按列表顺序写入码表，按需加整数 `weight`。菜单用 `code` 表示触发码、`label` 表示候选文字、`target` 表示选中后跳往的编码。

```yaml
words:
  - code: om
    label: 常用符号
    target: omfh
  - code: omfh
    text: "★"
    comment: 星号
top:
  - code: cesi
    text: 测试词
delete:
  - code: cesi
    text: 旧候选
```

也可以用命令管理。在仓库内可直接调用 `scripts/ime`。

```sh
ime add 猫咪 mcmi
ime top 微博 wb
ime del 拼音 py
ime apply
```

没有 personal.yaml 时仍可加载旧版 TXT/TSV 文件。第一次用命令写入会将现有条目一并转换到 YAML。已有 YAML 时只读取 YAML。个人源文件仅保存在本机。

## 输入习惯

| 输入 | 效果 |
|---|---|
| Control+F4 | 方案菜单，候选每页九项 |
| Escape | 有候选时选第二项，空闲时切换中英文 |
| Control+p / Control+n | 组合输入时上下选词 |
| `;`（空闲时） | 直接输入分号 |
| oa / ok / oc | 感叹号、成对圆括号、重复上屏 |
| og / ouj | 日期、时间 |
| ouok 加拆分码 | 上游拼字，例如 ouokhguu 输入“丁” |
| ouei / oujf | 二简次选开关、简繁切换 |
| 反引号 / 等号 | 小鹤反查、上游计算器 |

默认英文、英文标点。保留 o 快符的编码优先级，同时启用新版三码填空、二简次选与一简词。没有精确候选的普通三码，从四码主词表生成末键提示。基础词表位于 flypy/，生成时处理重码。新增本地规则可编辑 profile/flypy.custom.yaml。

Openfly Lua 移植自 amorphobia/openfly，保留 [MIT 许可证](lua/LICENSE.openfly)。o 快符表源于 Openfly v9.9m 本地变体，保留署名与[随附许可文本](profile/by-nc.md)。
