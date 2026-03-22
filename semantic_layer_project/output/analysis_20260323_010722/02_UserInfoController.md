# UserInfoController - API 语义层文档

> 自动生成的 API 语义层文档
>
> 生成时间：2026-03-23 01:07:22
>
> 文件路径：`F:\12306\services\user-service\src\main\java\org\opengoofy\index12306\biz\userservice\controller\UserInfoController.java`

---

## 📋 类概览

### 基本信息
- **类名**：UserInfoController
- **描述**：用户控制层
- **包路径**：org.opengoofy.index12306.biz.userservice.controller
- **业务域**：用户管理
- **API 数量**：6

### API 列表

1. **queryUserByUsername** - GET `/api/user-service/query`
   - 描述：用户控制层
   - 语义角色：查询 API

2. **queryActualUserByUsername** - GET `/api/user-service/actual/query`
   - 描述：根据用户名查询用户无脱敏信息
   - 语义角色：查询 API

3. **hasUsername** - GET `/api/user-service/has-username`
   - 描述：检查用户名是否已存在
   - 语义角色：操作 API

4. **register** - POST `/api/user-service/register`
   - 描述：注册用户
   - 语义角色：注册 API

5. **update** - POST `/api/user-service/update`
   - 描述：修改用户
   - 语义角色：更新 API

6. **deletion** - POST `/api/user-service/deletion`
   - 描述：注销用户
   - 语义角色：操作 API


---

## 📊 统计信息

### HTTP 方法分布

- **GET**：3 个
- **POST**：3 个

### 语义角色分布

- **查询 API**：2 个
- **操作 API**：2 个
- **注册 API**：1 个
- **更新 API**：1 个

---


## 1. queryUserByUsername

### 基本信息
- **方法名**：`queryUserByUsername`
- **描述**：用户控制层
- **HTTP 方法**：GET
- **URL**：`/api/user-service/query`
- **语义角色**：查询 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
用户控制层

**业务职责：**
检索并返回用户控制层

**操作类型：**
读操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserInfoController.queryUserByUsername()`
- HTTP：`GET /api/user-service/query`

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
- 当需要用户控制层时使用
- 这是只读操作，不会修改数据


**示例请求：**
```http
GET /api/user-service/query
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


## 2. queryActualUserByUsername

### 基本信息
- **方法名**：`queryActualUserByUsername`
- **描述**：根据用户名查询用户无脱敏信息
- **HTTP 方法**：GET
- **URL**：`/api/user-service/actual/query`
- **语义角色**：查询 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
根据用户名查询用户无脱敏信息

**业务职责：**
检索并返回根据用户名查询用户无脱敏信息

**操作类型：**
读操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserInfoController.queryActualUserByUsername()`
- HTTP：`GET /api/user-service/actual/query`

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
- 当需要根据用户名查询用户无脱敏信息时使用
- 这是只读操作，不会修改数据


**示例请求：**
```http
GET /api/user-service/actual/query
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


## 3. hasUsername

### 基本信息
- **方法名**：`hasUsername`
- **描述**：检查用户名是否已存在
- **HTTP 方法**：GET
- **URL**：`/api/user-service/has-username`
- **语义角色**：操作 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
检查用户名是否已存在

**业务职责：**
执行操作：检查用户名是否已存在

**操作类型：**
读操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserInfoController.hasUsername()`
- HTTP：`GET /api/user-service/has-username`

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
- 当需要检查用户名是否已存在时使用
- 这是只读操作，不会修改数据


**示例请求：**
```http
GET /api/user-service/has-username
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


## 4. register

### 基本信息
- **方法名**：`register`
- **描述**：注册用户
- **HTTP 方法**：POST
- **URL**：`/api/user-service/register`
- **语义角色**：注册 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
注册用户

**业务职责：**
执行操作：注册用户

**操作类型：**
写操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserInfoController.register()`
- HTTP：`POST /api/user-service/register`

**请求参数：**
- 无参数


**副作用：**
- 数据库操作：可能修改数据


**风险评估：**
- **风险级别**：HIGH
- **理由**：POST 操作，可能修改数据；识别到 1 个副作用；涉及敏感数据或重要操作

**幂等性：**
- **是否幂等**：否


### 上下文层

**注解：**


**使用指南：**

何时使用此 API：
- 当需要注册用户时使用
- 这是写操作，会修改数据


**示例请求：**
```http
POST /api/user-service/register
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
- ⚠️ 这是写操作，确保有适当的授权
- ⚠️ 调用前验证所有输入参数
- 🚨 HIGH 风险操作，需要特别注意

---


## 5. update

### 基本信息
- **方法名**：`update`
- **描述**：修改用户
- **HTTP 方法**：POST
- **URL**：`/api/user-service/update`
- **语义角色**：更新 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
修改用户

**业务职责：**
更新现有的修改用户

**操作类型：**
写操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserInfoController.update()`
- HTTP：`POST /api/user-service/update`

**请求参数：**
- 无参数


**副作用：**
- 数据库写入：更新现有记录


**风险评估：**
- **风险级别**：HIGH
- **理由**：POST 操作，可能修改数据；识别到 1 个副作用；涉及敏感数据或重要操作

**幂等性：**
- **是否幂等**：否


### 上下文层

**注解：**


**使用指南：**

何时使用此 API：
- 当需要修改用户时使用
- 这是写操作，会修改数据


**示例请求：**
```http
POST /api/user-service/update
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
- ⚠️ 这是写操作，确保有适当的授权
- ⚠️ 调用前验证所有输入参数
- 🚨 HIGH 风险操作，需要特别注意

---


## 6. deletion

### 基本信息
- **方法名**：`deletion`
- **描述**：注销用户
- **HTTP 方法**：POST
- **URL**：`/api/user-service/deletion`
- **语义角色**：操作 API
- **业务域**：用户管理

### 语义层

**这个 API 做什么：**
注销用户

**业务职责：**
执行操作：注销用户

**操作类型：**
写操作

**置信度：** 0.90
- 基于：URL 模式、HTTP 方法、方法名和注解

### 行为层

**执行模式：** REST API 端点

**入口点：**
- 方法：`UserInfoController.deletion()`
- HTTP：`POST /api/user-service/deletion`

**请求参数：**
- 无参数


**副作用：**
- 数据库操作：可能修改数据


**风险评估：**
- **风险级别**：MEDIUM
- **理由**：POST 操作，可能修改数据；识别到 1 个副作用

**幂等性：**
- **是否幂等**：否


### 上下文层

**注解：**


**使用指南：**

何时使用此 API：
- 当需要注销用户时使用
- 这是写操作，会修改数据


**示例请求：**
```http
POST /api/user-service/deletion
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
- ⚠️ 这是写操作，确保有适当的授权
- ⚠️ 调用前验证所有输入参数

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
