mvn spring-boot:run  

​	可以通过-Dspring-boot.run.fork=false带来绕过命令行限制

​	其实在springboot3.x版本中自己解决了命令行的问题

​	



mvn spring-boot:run -o -pl 你的主模块名 -Dspring-boot.run.fork=false
   两个参数各解决一个问题：

---

   ### `-o` → 离线模式，禁止下载

   Maven 全程不走网络，只读本地仓库
   ~/.m2/repository。如果本地缺依赖，直接报错而不是去下载——这样你能一眼看到是缺东西还是白白重复下载。

   如果报错说缺依赖，说明之前就没下载完整，跑一遍：
   [bash]
   mvn compile -pl 你的主模块名 -am
   先把依赖全部拉到本地，之后加上 -o 就再也不会去联网了。

---

---

   ## 完整操作流程
   [bash]
   # 第一步：一次性拉齐依赖（只要没新增依赖，这步只做一次）
   mvn compile -pl your-web-module -am

   # 第二步：之后每次都这样跑——离线 + 同进程，秒启
   mvn spring-boot:run -o -pl your-web-module -Dspring-boot.run.fork=false
   ---

   ## 如果还被要求传 JVM 参数怎么办

   fork=false 时自定义 JVM 参数会被忽略。如果确需传参（比如 -Xmx），就只能走 fork，但 fork 又撞上 classpath
   长度限制。这时有两个选择：

   A. 用 MAVEN_OPTS 设给 Maven 本身（fork=false 时应用继承了 Maven JVM 的参数）：
   [bash]
   MAVEN_OPTS="-Xmx2g -Dfile.encoding=UTF-8" mvn spring-boot:run -o -pl your-module -Dspring-boot.run.fork=false
   B. fork 模式下手动构造短 classpath——但这基本不现实，不推荐。

---

   ## 总结

| 参数                         | 解决的问题                      |
| ---------------------------- | ------------------------------- |
| -o                           | 禁网络，不再重复下载            |
| -Dspring-boot.run.fork=false | 同 JVM 启动，绕开命令行长度限制 |
| -pl 模块名                   | 指定主模块，避免扫全项目        |



 > 那我使用这个命令启动程序的话   程序日志可以放在一个文件中吗   我不想在命令行看到日志

 ✦ 两个办法，一个不改代码，一个改一行配置。

---

   ## 方案一：不改代码，纯命令搞定
   [bash]
   mvn spring-boot:run -o -pl your-module -Dspring-boot.run.fork=false \
     -Dspring-boot.run.arguments="--logging.file.name=logs/app.log" \
     > /dev/null 2>&1
   拆开看：

| 部分                             | 作用                                                     |
| -------------------------------- | -------------------------------------------------------- |
| --logging.file.name=logs/app.log | Spring Boot 自带的，日志追加写入文件，同时控制台仍然输出 |
| > /dev/null 2>&1                 | 把控制台剩下的日志扔进黑洞                               |

   这样一来：文件里有完整日志，控制台干干净净。

   │ > /dev/null 是 Git Bash / Linux 写法，如果你用 Windows CMD，改成 > NUL 2>&1

---

   ## 方案二：改一行配置，控制台彻底静默

   在 src/main/resources/application.properties（或 yml）里加一行：
   [properties]
   logging.file.name=logs/app.log
   然后在 logback-spring.xml 里关掉 console appender：
   [xml]
   <!-- src/main/resources/logback-spring.xml -->
   <configuration>
       <!-- 只写文件，不输出控制台 -->
       <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
           <file>logs/app.log</file>
           <encoder>
               <pattern>%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n</pattern>
           </encoder>
           <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
               <fileNamePattern>logs/app.%d{yyyy-MM-dd}.%i.log</fileNamePattern>
               <maxFileSize>100MB</maxFileSize>
               <maxHistory>30</maxHistory>
           </rollingPolicy>
       </appender>

       <root level="INFO">
           <appender-ref ref="FILE" />
           <!-- 没有 CONSOLE appender → 控制台不输出 -->
       </root>
   </configuration>
   之后直接跑，控制台不会出现任何应用日志：
   [bash]
   mvn spring-boot:run -o -pl your-module -Dspring-boot.run.fork=false
   ---

   ## 选哪个

| 方案   | 改动     | 控制台                        | 文件 |
| ------ | -------- | ----------------------------- | ---- |
| 方案一 | 无       | 静默（连 Maven 输出一起扔了） | ✅    |
| 方案二 | 配置文件 | 只静默应用日志，Maven 的还在  | ✅    |

   日常开发推荐方案二，一劳永逸。方案一适合临时调试、不想动项目代码的情况。





 ## 一句话
   mvn spring-boot:run -pl web-module -am
   -am 把同级依赖模块拉进同一次构建，Maven 的 Reactor 机制直接指向它们的 target/classes/，compile 就够，不需要
   install。

   只有当你分开跑、不靠 Reactor 的时候：
   [bash]
   # 先单独跑 web-module，同级模块不在 Reactor 里
   mvn spring-boot:run -pl web-module    # ← 这时候才需要 common-module 提前 install
   才需要 install。加了 -am 就没这事了。