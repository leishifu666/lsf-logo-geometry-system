# 参数与命令契约

## 依赖

构造：Python 3.10+ 标准库。测量：Pillow、NumPy。可选 SVG→PNG：Node.js + `sharp`。技能无联网运行要求；不调用远程分析服务。使用环境已有依赖，缺失时只补这些项，不依赖机器固定路径。

在技能目录下：

```text
python scripts/build_sheet.py examples/tidebank.json --out <新输出目录>
node scripts/render_svg.cjs <输出目录>/construction.svg <输出目录>/construction.png 1600
python scripts/measure.py compare original.png rebuilt.png --out metrics.json --diff difference.png --max-mean-pct 0.5 --max-p95-pct 1
python scripts/measure.py fit-circle selected-arc.csv --out circle-fit.json
```

`sharp` 通过普通 Node 模块解析；环境提供统一依赖目录时可临时设置 `NODE_PATH`。文件系统路径和运行时路径由当前环境获取，不写入几何文件。

## 几何 JSON

### 圆角组件构造器（独立于下方制图 JSON）

`round_polygon.py` 输入 `vertices: [[x,y],...]` 和同长度 `radii: [r0,r1,...]`。顶点沿轮廓顺序列出，尾点不重复首点；0 表示有意保留尖角。只适用于简单多边形的直线—直线倒圆，不支持孔洞、既有圆弧或任意 SVG 自动圆角化。

```text
python scripts/round_polygon.py examples/rounded-corner.json --out rounded-test
```

输出 `master.svg`、`inverse.svg`、`construction.svg`、`geometry.json`。成品与构造圆来自同一函数；可用输入 JSON 再运行复建。它检查切点和相邻圆角占边，不验证全局自交，也不识别哪处该用多大圆角；需要渲染并检查轮廓和负形。`construction.svg` 是组件构造图，完整品牌制图页按当前任务另行编排。默认拒绝覆盖已有同名输出。

### 标准制图构造器

所有坐标以 x 为单位，`module.value` 表示一个 x 等于多少设计单位，SVG 的 viewBox 使用 x 坐标。正 x 向右、正 y 向下；正角顺时针。

- `title/subtitle/status`：展示文字。
- `bounds: [xmin,ymin,width,height]`：声明的实绘包围盒，用于主标志 viewBox；脚本不求解析极值，必须自行核对，错误值可能裁切。
- `module: {value,unit}`：正数模块与单位名。
- `shapes[]`：每项有唯一 `id`、`type`、几何字段、证据字段；可用 `rotate:[角度,中心x,中心y]`。
- `operation` 缺省 `add`；`subtract` 从全部相加图形中统一扣除。**先并所有 add，再减所有 subtract**；不支持交替 CSG 顺序。mask 实现透明负形。
- `measurements[]`：`label,ref` 必填，`ref` 是 JSON 数值路径，例如 `shapes.0.outer_radius`；`factor/offset` 缺省 1/0；显示值=`ref*factor+offset`；单位缺省 x，可写 `" deg"`。制图页最多 8 行，更多尺寸另附说明。
- `sheet_style`：缺省 `proportion`，输出 B 式比例定位主图。`path-detail` 显式选择旧式四区细节页；不会自动生成完整自由曲线控制柄。

### B 式定位线与图上尺寸

`construction` 可包含以下字段。复杂排版、文字标志与局部放大可用项目脚本制作，仍遵循 [制图表达](construction-presentation.md)。

- `module_definition`：说明 x 的选取依据，例如「本次定义 x = 共用间隙」。`evidence_note`：辅助线依据或局限的简短说明。
- `guides[]`：`type: line` 时提供 `from/to: [x,y]`，默认 `extend: true` 延长到制图区域；`extend: false` 保留线段。`type: circle` 时提供 `center: [x,y]` 和 `radius`。每条必须有 `basis` 说明对应的直边、圆弧或定位关系；脚本检查字段和几何数值，不自动证明文字依据。
- `dimensions[]`：提供被测端点 `from/to`；长度由两点欧氏距离计算，按 x 输出。`offset` 为尺寸线沿左法向偏移量（几何 x 单位），同时生成尺寸界线。`prefix: "R "` 可标半径；可用 `text_offset: [dx,dy]` 调整文字，单位为页面像素。斜边宽度/间隙的两个端点必须由几何按法向生成，脚本不会猜测。角度标注及局部放大用项目脚本处理。
- 坐标、半径、offset 可写数值、数值字段路径字符串，或 `{"ref":"字段路径","factor":1,"offset":0}`。优先引用同源参数，不能复制一份会过期的尺寸。
- 缺省尺寸为声明包围框的宽高；缺省定位线为声明框的四边和中心轴。仅圆、椭圆、圆环段、胶囊原语自动提供对应构造线。自由路径不会自动生成猜测圆，也不能只靠缺省包围框就宣称已完成复杂制图；应补入实际定位关系。
- 明确传 `dimensions: []` 可省略默认尺寸，例如所有尺寸已在独立细节图说明。注意：输入坐标本来就在 x 单位中，`module.value` 是一个 x 对应的原设计单位数，不会再次除以它。

见 `examples/proportion-guides.json` 的同源字段引用。改动其 `shapes.0.width` 时，胶囊、图上宽度尺寸及圆心定位参考线会一起更新；声明的包围框仍需调用方核对。

原语字段：

| type | 字段 |
|---|---|
| circle | cx,cy,r |
| ellipse | cx,cy,rx,ry |
| rect | x,y,width,height,radius（可选） |
| capsule | x,y,width,height；自动端圆半径=min(width,height)/2 |
| polygon | points:[[x,y],...] |
| annular-sector | cx,cy,outer_radius,inner_radius,start_deg,sweep_deg；sweep 为 0–360 之间的正数，不含端点 |
| path | d，fill_rule（可选 nonzero/evenodd）；原始自由曲线应保留此形态 |

同一个图形多次旋转需要显式复制对象并赋不同 ID；脚本不猜对称性。圆环全周用一个 add 圆、一个 subtract 圆；圆环段直接使用 annular-sector。路径只接受路径指令/数值，不嵌入 SVG 脚本、外链图片或任意 XML。

工具自动生成圆环段的同心构造圆和边界射线，圆的中心十字、胶囊端圆以及原语轮廓。自由 path 不自动发明辅助圆。更复杂的布尔或标注可编写本项目构造器，不假称当前工具支持。

## 测量限制

`compare` 要求同画布、同配准，不进行对齐。默认将透明图合成白底后按亮度分割；纯透明轮廓可用 `--mask alpha`。结果包含原图实绘最大尺寸 D、像素偏差、占 D 的百分比、IoU、前景 8 邻域组件和背景 4 邻域孔洞。

返回码 0 表示所请求的数值门槛和拓扑检查通过；2 表示检查不通过。未设数值门槛时，0 **不代表轮廓合格**。`sampled=true` 时所有距离基于降采样边界。差异图红=仅原图、蓝=仅重建、深灰=交集。

`fit-circle` 是代数最小二乘的候选拟合，不是稳健分段或自动去噪器。CSV 无表头、每行 x,y；短弧会提示不稳定，噪声点、轮廓分段和其他模型由使用者检查。

脚本不会自动识别任意品牌、恢复丢失像素、找出原作者意图或认证商标。它们为技能执行提供可复查的构造和测量步骤。

## 复跑本包示例

`examples/run_validation.py --out <空目录>` 用解析不等式生成独立位图，再对该案例选择的圆环/节点区域测量，输出重建 JSON/SVG、故意移动节点的 SVG、透明扣孔样本。它只针对已识别的本案例结构，开口方向和模块选择是已知假设，不代表任意 Logo 自动识别。

```text
python -m unittest discover -s tests -v
python examples/run_validation.py --out <空目录>
node scripts/render_svg.cjs <目录>/reconstruction/master.svg <目录>/reconstruction/master.png 800
node scripts/render_svg.cjs <目录>/mutated/master.svg <目录>/mutated/master.png 800
python scripts/measure.py compare <目录>/raster-input.png <目录>/reconstruction/master.png --max-mean-pct 0.5 --max-p95-pct 1
python scripts/measure.py compare <目录>/raster-input.png <目录>/mutated/master.png --max-mean-pct 0.5 --max-p95-pct 1
```

最后一条预期返回 2，表示故意制造的错误被检出。精确误差会随渲染器版本变化。
