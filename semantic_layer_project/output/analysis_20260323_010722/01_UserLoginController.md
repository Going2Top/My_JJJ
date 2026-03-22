# UserLoginController - API 语义层文档

> 自动生成的 API 语义层文档
>
> 生成时间：2026-03-23 01:07:22
>
> 文件路径：`F:\12306\services\user-service\src\main\java\org\opengoofy\index12306\biz\userservice\controller\UserLoginController.java`

---

## 📋 类概览

### 基本信息
- **类名**：UserLoginController
- **描述**：用户登录控制层
- **包路径**：org.opengoofy.index12306.biz.userservice.controller
- **业务域**：用户管理
- **API 数量**：3

### API 列表

1. **login** - POST `/api/user-service/v1/login`
   - 描述：用户登录控制层
   - 语义角色：认证 API

2. **checkLogin** - GET `/api/user-service/check-login`
   - 描述：通过 Token 检查用户是否登录
   - 语义角色：认证 API

3. **logout** - GET `/api/user-service/logout`
   - 描述：用户退出登录
   - 语义角色：登出 API


---

## 📊 统计信息

### HTTP 方法分布

- **GET**：2 个
- **POST**：1 个

### 语义角色分布

- **认证 API**：2 个
- **登出 API**：1 个

---


## 1. login

### 基本信息
- **方法名**：`login`
- **描述**：用户登录控制层
- **HTTP 方法**：POST
- **URL**：`/api/user-service/v1/login`
- **语义角色**：认证 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
用户登录控制层

**业务职责：**
验证用户身份并用户登录控制层

**操作类型：**
写操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserLoginController.login()`
- HTTP：`POST /api/user-service/v1/login`

**请求参数：**
- **requestParam** (UserLoginReqDTO) - @RequestBody


**副作用：**
- 会话管理：创建用户会话
- 缓存写入：存储认证令牌


**风险评估：**
- **风险级别**：HIGH
- **理由**：POST 操作，可能修改数据；识别到 2 个副作用；涉及敏感数据或重要操作

**幂等性：**
- **是否幂等**：否


### 上下文层

**注解：**


**使用指南：**

何时使用此 API：
- 当需要用户登录控制层时使用
- 这是写操作，会修改数据


**示例请求：**
```http
POST /api/user-service/v1/login
Content-Type: application/json
```

**请求体：**
```json
{
  // UserLoginReqDTO 对象
}
```


**响应示例：**
```json
{
  "code": "0",
  "message": "success",
  "data": { ... }
}
```

**重要提示：**
- ⚠️ 这是写操作，确保有适当的授权
- ⚠️ 调用前验证所有输入参数
- 🚨 HIGH 风险操作，需要特别注意

---


## 2. checkLogin

### 基本信息
- **方法名**：`checkLogin`
- **描述**：通过 Token 检查用户是否登录
- **HTTP 方法**：GET
- **URL**：`/api/user-service/check-login`
- **语义角色**：认证 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
通过 Token 检查用户是否登录

**业务职责：**
验证用户身份并通过 Token 检查用户是否登录

**操作类型：**
读操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserLoginController.checkLogin()`
- HTTP：`GET /api/user-service/check-login`

**请求参数：**
- 无参数


**副作用：**
- 无副作用（只读操作）


**风险评估：**
- **风险级别**：LOW
- **理由**：GET 操作，只读，不修改数据

**幂等性：**
- **是否幂等**：否


### 上下文层

**注解：**


**使用指南：**

何时使用此 API：
- 当需要通过 Token 检查用户是否登录时使用
- 这是只读操作，不会修改数据


**示例请求：**
```http
GET /api/user-service/check-login
Content-Type: application/json
```


**响应示例：**
```json
{
  "code": "0",
  "message": "success",
  "data": { ... }
}
```

**重要提示：**

---


## 3. logout

### 基本信息
- **方法名**：`logout`
- **描述**：用户退出登录
- **HTTP 方法**：GET
- **URL**：`/api/user-service/logout`
- **语义角色**：登出 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
用户退出登录

**业务职责：**
执行操作：用户退出登录

**操作类型：**
读操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserLoginController.logout()`
- HTTP：`GET /api/user-service/logout`

**请求参数：**
- 无参数


**副作用：**
- 无副作用（只读操作）


**风险评估：**
- **风险级别**：LOW
- **理由**：GET 操作，只读，不修改数据

**幂等性：**
- **是否幂等**：否


### 上下文层

**注解：**


**使用指南：**

何时使用此 API：
- 当需要用户退出登录时使用
- 这是只读操作，不会修改数据


**示例请求：**
```http
GET /api/user-service/logout
Content-Type: application/json
```


**响应示例：**
```json
{
  "code": "0",
  "message": "success",
  "data": { ... }
}
```

**重要提示：**

---


## 📚 附录

### 架构模式
- **模式**：Spring MVC Controller-Service 架构
- **层级**：Controller 层（API 入口点）
- **职责**：处理 HTTP 请求，委托给 Service 层

### 命名规范
- **Controller**：PascalCase，以 'Controller' 结尾
- **方法**：camelCase，动词开头
- **URL**：kebab-case，RESTful 风格

### 响应格式
- 统一包装在 `Result<T>` 中
- 使用 `Results.success()` 辅助方法构造响应

---

*由 AI Agent 语义层生成系统生成*
