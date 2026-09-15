---
name: code-review
description: 进行全面的代码审查，包括安全性、性能和可维护性分析。适用于用户要求审查代码、检查错误或审计代码库时。
---

# 代码审查技能

你现在具备进行全面代码审查的专业能力。请遵循以下结构化方法：

## 审查清单

### 1. 安全性（关键）

检查：
- [ ] **注入漏洞**：SQL 注入、命令注入、XSS、模板注入
- [ ] **身份认证问题**：硬编码凭据、薄弱的认证机制
- [ ] **授权缺陷**：缺少访问控制、IDOR
- [ ] **数据泄露**：日志或错误消息中包含敏感数据
- [ ] **密码学问题**：薄弱算法、密钥管理不当
- [ ] **依赖项**：已知漏洞（使用 `npm audit`、`pip-audit` 检查）

```bash
# 快速安全扫描
npm audit                    # Node.js
pip-audit                    # Python
cargo audit                  # Rust
grep -r "password\|secret\|api_key" --include="*.py" --include="*.js"
```

### 2. 正确性

检查：
- [ ] **逻辑错误**：差一错误、空值处理、边界情况
- [ ] **竞态条件**：并发访问时缺少同步
- [ ] **资源泄漏**：文件、连接或内存未释放
- [ ] **错误处理**：异常被吞掉、缺少错误路径
- [ ] **类型安全**：隐式转换、any 类型

### 3. 性能

检查：
- [ ] **N+1 查询**：循环中调用数据库
- [ ] **内存问题**：大块内存分配、引用未释放
- [ ] **阻塞操作**：异步代码中的同步 I/O
- [ ] **低效算法**：可使用 O(n) 时却使用 O(n²)
- [ ] **缺少缓存**：重复执行开销高昂的计算

### 4. 可维护性

检查：
- [ ] **命名**：清晰、一致、描述准确
- [ ] **复杂度**：函数超过 50 行、嵌套超过 3 层
- [ ] **重复**：复制粘贴的代码块
- [ ] **无用代码**：未使用的导入、不可达分支
- [ ] **注释**：过时、冗余，或在必要位置缺失

### 5. 测试

检查：
- [ ] **覆盖率**：关键路径得到测试
- [ ] **边界情况**：空值、空内容、边界值
- [ ] **模拟**：外部依赖已隔离
- [ ] **断言**：检查有意义且具体

## 审查输出格式

```markdown
## 代码审查：[文件/组件名称]

### 摘要
[用 1～2 句话概述]

### 严重问题
1. **[问题]**（第 X 行）：[描述]
   - 影响：[可能出现的问题]
   - 修复：[建议的解决方案]

### 改进建议
1. **[建议]**（第 X 行）：[描述]

### 值得肯定之处
- [做得好的地方]

### 结论
[ ] 可以合并
[ ] 需要少量修改
[ ] 需要大幅修改
```

## 常见需标记模式

### Python
```python
# 错误：SQL 注入
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# 正确：
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# 错误：命令注入
os.system(f"ls {user_input}")
# 正确：
subprocess.run(["ls", user_input], check=True)

# 错误：可变默认参数
def append(item, lst=[]):  # 缺陷：共享可变默认值
# 正确：
def append(item, lst=None):
    lst = lst or []
```

### JavaScript/TypeScript
```javascript
// 错误：原型污染
Object.assign(target, userInput)
// 正确：
Object.assign(target, sanitize(userInput))

// 错误：使用 eval
eval(userCode)
// 正确：绝不要对用户输入使用 eval

// 错误：回调地狱
getData(x => process(x, y => save(y, z => done(z))))
// 正确：
const data = await getData();
const processed = await process(data);
await save(processed);
```

## 审查命令

```bash
# 显示最近的更改
git diff HEAD~5 --stat
git log --oneline -10

# 查找潜在问题
grep -rn "TODO\|FIXME\|HACK\|XXX" .
grep -rn "password\|secret\|token" . --include="*.py"

# 检查复杂度（Python）
pip install radon && radon cc . -a

# 检查依赖项
npm outdated  # Node
pip list --outdated  # Python
```

## 审查工作流

1. **理解上下文**：阅读 PR 描述和关联的问题
2. **运行代码**：如果可行，在本地构建、测试并运行
3. **自上而下阅读**：从主要入口点开始
4. **检查测试**：更改是否经过测试？测试是否通过？
5. **安全扫描**：运行自动化工具
6. **人工审查**：使用上述清单
7. **编写反馈**：具体说明问题、提出修复建议并保持友善
